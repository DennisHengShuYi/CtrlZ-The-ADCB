import { useState, useEffect } from 'react';
import { useUser } from '@clerk/clerk-react';
import { useApiFetch } from '../../hooks/useApiFetch';
import { ShieldCheck, CheckCircle2, Globe, TrendingUp } from 'lucide-react';
import { motion } from 'framer-motion';
import { jsPDF } from 'jspdf';

const TIERS = [
    { id: 'pre-bronze', name: 'Pre-Bronze', label: 'Unregistered Active', color: '#64748b', bg: '#f1f5f9', icon: '🔍', desc: 'Recognized by AI ledger based on e-invoices, but no legal SSM registration.', checklist: 'Generate first invoice (Pre-Bronze)' },
    { id: 'bronze', name: 'Bronze', label: 'Bronze Real', color: '#b45309', bg: '#fef3c7', icon: '🥉', desc: 'Verified as a registered business entity within Malaysia via SSM connection.', checklist: 'Register with SSM (Bronze)' },
    { id: 'silver', name: 'Silver', label: 'Silver Cash Flow', color: '#475569', bg: '#e2e8f0', icon: '🥈', desc: 'Operationally capable with 6 months of positive cash flow & revenue consistency.', checklist: 'Maintain 6-months positive cashflow (Silver)' },
    { id: 'gold', name: 'Gold', label: 'Gold Ready to Export', color: '#b45309', bg: '#fef08a', icon: '🥇', desc: 'Tax compliant, legally registered, and regulatory verified for export readiness.', checklist: 'Submit Annual Form C & SSM Return (Gold)' },
    { id: 'platinum', name: 'Platinum', label: 'Platinum Global Ready', color: '#0f172a', bg: '#cbd5e1', icon: '💎', desc: 'Demonstrated international trade experience and cross-border sales.', checklist: 'Process First International Foreign Currency Invoice (Platinum)' },
    { id: 'diamond', name: 'Diamond', label: 'Diamond Trusted Partner', color: '#1d4ed8', bg: '#dbeafe', icon: '💠', desc: 'Highly investable, exceptional credit score, bank-backed trust history.', checklist: 'Achieve ≥95% Loan Readiness Score (Diamond)' },
];

const PassportPage = () => {
    const { user } = useUser();
    const apiFetch = useApiFetch();
    const [loading, setLoading] = useState(true);
    
    // Extracted Status
    const [companyInfo, setCompanyInfo] = useState<any>(null);
    const [analysisData, setAnalysisData] = useState<any>(null);
    
    // Grading
    const [activeTierIdx, setActiveTierIdx] = useState(0);

    useEffect(() => {
        const fetchPassportData = async () => {
            if (!user) return;
            try {
                const ts = Date.now();
                const email = user.primaryEmailAddress?.emailAddress || '';
                
                const [company, analysis, invoicesRes, staffRes] = await Promise.all([
                    apiFetch(`/api/company?t=${ts}&email=${encodeURIComponent(email)}`),
                    apiFetch(`/api/analysis?t=${ts}`),
                    apiFetch(`/api/invoices/?t=${ts}`), // we need this to check currency
                    apiFetch(`/api/staff?t=${ts}`).catch(() => ({ staff: [] })),
                ]);
                
                const invoicesArr = invoicesRes.invoices || [];
                const staffArr = staffRes.staff || staffRes || [];
                
                // --- Real Time Currency Conversion Setup ---
                const uniqueCurrencies = Array.from(new Set(invoicesArr.map((i: any) => i.currency).filter((c: any) => c && c !== 'MYR')));
                const rates: Record<string, number> = {};
                await Promise.all(
                    uniqueCurrencies.map(async (curr) => {
                        try {
                            const rt = await apiFetch(`/api/currency/rate?from=${curr}&to=MYR`);
                            if (rt && rt.rate) {
                                rates[curr as string] = rt.rate;
                            }
                        } catch (e) {
                            console.error(`Failed to fetch rate for ${curr}`, e);
                        }
                    })
                );

                setCompanyInfo(company);
                setAnalysisData(analysis);
                
                calculateTier(company, analysis, invoicesArr, rates, staffArr);
            } catch (err) {
                console.error("Failed to load DMI Passport data", err);
            } finally {
                setLoading(false);
            }
        };
        fetchPassportData();
    }, [user, apiFetch]);

    const calculateTier = (company: any, analysis: any, invoices: any[], rates: Record<string, number> = {}, staff: any[] = []) => {
        let tierIndex = 0; // Pre-Bronze by default if they have some data
        
        const hasRegistration = !!company?.business_reg;
        const revenue = analysis?.totalRevenue || 0;

        const revenueConsistency = analysis?.revenueConsistency || 0;
        
        let hasInternational = false;
        let positiveCashFlowMonthsRatio = 0;
        
        if (invoices && Array.isArray(invoices)) {
            // Platinum: only count customer invoices (invoice_number starts with 'M') in a non-MYR currency
            hasInternational = invoices.some(inv =>
                inv.invoice_number &&
                (inv.invoice_number.toUpperCase().startsWith('M') || inv.invoice_number.toUpperCase().startsWith('INV')) &&
                inv.currency &&
                inv.currency.toUpperCase() !== 'MYR'
            );

            // Calculate real cash flow for the past 6 months (invoices + staff salary deducted)
            const monthlyPayroll = Array.isArray(staff)
                ? staff.reduce((sum: number, s: any) => sum + (Number(s.salary) || 0), 0)
                : 0;

            console.group('📊 Positive Cash Flow Ratio — Calculation Debug');
            console.log(`Staff count        : ${Array.isArray(staff) ? staff.length : 0}`);
            console.log(`Monthly Payroll    : RM ${monthlyPayroll.toFixed(2)}`);
            console.log(`Exchange rates     :`, rates);
            console.log(`Total invoices     : ${invoices.length}`);

            const monthlyCashFlow: Record<string, number> = {};
            const monthlyBreakdown: Record<string, { customerInv: number; supplierInv: number; beforePayroll: number; afterPayroll: number }> = {};

            invoices.forEach(inv => {
                if (!inv.date) return;
                const month = inv.date.substring(0, 7);
                let amount = Number(inv.total_amount) || 0;
                const origAmount = amount;
                const origCurrency = inv.currency || 'MYR';
                if (inv.currency && inv.currency.toUpperCase() !== 'MYR') {
                    const conversionRate = rates[inv.currency] || 1;
                    amount = amount * conversionRate;
                }
                const isIssuing = inv.invoice_number && (inv.invoice_number.toUpperCase().startsWith('M') || inv.invoice_number.toUpperCase().startsWith('INV'));
                if (!monthlyBreakdown[month]) monthlyBreakdown[month] = { customerInv: 0, supplierInv: 0, beforePayroll: 0, afterPayroll: 0 };
                if (isIssuing) {
                    monthlyCashFlow[month] = (monthlyCashFlow[month] || 0) + amount;
                    monthlyBreakdown[month].customerInv += amount;
                    console.log(`  [${month}] ✅ CUSTOMER  ${inv.invoice_number} | ${origCurrency} ${origAmount.toFixed(2)} → RM ${amount.toFixed(2)}`);
                } else {
                    monthlyCashFlow[month] = (monthlyCashFlow[month] || 0) - amount;
                    monthlyBreakdown[month].supplierInv += amount;
                    console.log(`  [${month}] 🔴 SUPPLIER  ${inv.invoice_number} | ${origCurrency} ${origAmount.toFixed(2)} → RM ${amount.toFixed(2)}`);
                }
            });

            // Subtract monthly payroll from every month that has data
            Object.keys(monthlyCashFlow).forEach(month => {
                monthlyBreakdown[month].beforePayroll = monthlyCashFlow[month];
                monthlyCashFlow[month] -= monthlyPayroll;
                monthlyBreakdown[month].afterPayroll = monthlyCashFlow[month];
            });

            // Get the last 6 months that have data
            const months = Object.keys(monthlyCashFlow).sort().reverse().slice(0, 6);

            console.log('\n--- Monthly Summary (last 6 months) ---');
            months.forEach(m => {
                const b = monthlyBreakdown[m];
                const sign = monthlyCashFlow[m] > 0 ? '✅ POSITIVE' : '❌ NEGATIVE';
                console.log(`  ${m} | CustomerRev: RM ${b.customerInv.toFixed(2)} | SupplierExp: RM ${b.supplierInv.toFixed(2)} | BeforePayroll: RM ${b.beforePayroll.toFixed(2)} | Payroll: -RM ${monthlyPayroll.toFixed(2)} | Net: RM ${monthlyCashFlow[m].toFixed(2)}  ${sign}`);
            });

            if (months.length > 0) {
                const positiveMonths = months.filter(m => monthlyCashFlow[m] > 0).length;
                positiveCashFlowMonthsRatio = (positiveMonths / months.length) * 100;
                console.log(`\nPositive months    : ${positiveMonths} / ${months.length}`);
                console.log(`Cash Flow Ratio    : ${positiveCashFlowMonthsRatio.toFixed(2)}%  (need > 70% for Silver)`);
            }
            console.groupEnd();
        }
        
        const loanProb = analysis?.loanApprovalProbability || 0;
        
        // 1. Bronze (Has SSM Registration)
        if (hasRegistration) {
            tierIndex = 1;
            
            // 2. Silver (Bronze + Revenue > 0 + Real Cash Flow Ratio > 70 AND Revenue Consistency > 70)
            if (revenue > 0 && positiveCashFlowMonthsRatio > 70 && revenueConsistency > 70) {
                tierIndex = 2;
                
                // 3. Gold (Silver + Explicit Compliance Status)
                if (company?.compliance_status === 1) {
                    tierIndex = 3;
                    
                    // 4. Platinum (Gold + International Invoices)
                    if (hasInternational) {
                        tierIndex = 4;
                        
                        // 5. Diamond (Platinum + Loan Readiness >= 95)
                        if (loanProb >= 95) {
                            tierIndex = 5;
                        }
                    }
                }
            }
        }
        
        setActiveTierIdx(tierIndex);
    };

    const generateBankExportProfile = () => {
        const tier = TIERS[activeTierIdx];
        const now = new Date();
        const dateStr = now.toLocaleDateString('en-MY', { year: 'numeric', month: 'long', day: 'numeric' });
        const timeStr = now.toLocaleTimeString('en-MY');
        const fileName = `DMI_BankExportProfile_${(companyInfo?.name || 'Company').replace(/\s+/g, '_')}_${now.toISOString().slice(0, 10)}.pdf`;

        const doc = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4' });
        const W = 210;
        const margin = 18;
        let y = 0;

        // ── Header Banner ──────────────────────────────────────────────────────
        doc.setFillColor(15, 23, 42);      // #0f172a
        doc.rect(0, 0, W, 42, 'F');

        doc.setTextColor(255, 255, 255);
        doc.setFontSize(9);
        doc.setFont('helvetica', 'normal');
        doc.text('CTRLZ ADCB  ·  ASEAN TRUST LEDGER', margin, 12);

        doc.setFontSize(17);
        doc.setFont('helvetica', 'bold');
        doc.text('Verified Bank Export Profile', margin, 24);

        doc.setFontSize(8);
        doc.setFont('helvetica', 'normal');
        doc.text('Digital Maturity Index (DMI)  ·  ASEAN Capability Passport', margin, 31);
        doc.text(`Generated: ${dateStr}  ${timeStr}`, margin, 37);

        // Tier badge (top-right)
        const tierColors: Record<string, [number,number,number]> = {
            'pre-bronze': [100,116,139], bronze: [180,83,9],
            silver: [71,85,105],        gold: [180,83,9],
            platinum: [15,23,42],       diamond: [29,78,216],
        };
        const [tr, tg, tb] = tierColors[tier.id] || [100,116,139];
        doc.setFillColor(tr, tg, tb);
        doc.roundedRect(W - margin - 38, 8, 38, 26, 4, 4, 'F');
        doc.setTextColor(255, 255, 255);
        doc.setFontSize(7);
        doc.setFont('helvetica', 'bold');
        doc.text('CURRENT TIER', W - margin - 19, 16, { align: 'center' });
        doc.setFontSize(9);
        doc.text(tier.name.toUpperCase(), W - margin - 19, 23, { align: 'center' });
        doc.setFontSize(7);
        doc.setFont('helvetica', 'normal');
        doc.text(tier.label, W - margin - 19, 29, { align: 'center' });

        y = 52;

        // ── Section helper ─────────────────────────────────────────────────────
        const section = (title: string) => {
            doc.setFillColor(241, 245, 249);
            doc.rect(margin, y, W - margin * 2, 7, 'F');
            doc.setTextColor(30, 41, 59);
            doc.setFontSize(9);
            doc.setFont('helvetica', 'bold');
            doc.text(title, margin + 2, y + 5);
            y += 10;
        };

        const row = (label: string, value: string, highlight = false) => {
            doc.setFontSize(8.5);
            doc.setFont('helvetica', 'normal');
            doc.setTextColor(highlight ? 5 : 71, highlight ? 150 : 85, highlight ? 105 : 105);
            doc.text(label, margin + 2, y);
            doc.setTextColor(15, 23, 42);
            doc.setFont('helvetica', 'bold');
            doc.text(value, W - margin - 2, y, { align: 'right' });
            doc.setDrawColor(226, 232, 240);
            doc.line(margin, y + 1.5, W - margin, y + 1.5);
            y += 7;
        };

        // ── Company Information ────────────────────────────────────────────────
        section('COMPANY INFORMATION');
        row('Company Name',  companyInfo?.name || 'N/A');
        row('SSM Reg. No.',  companyInfo?.business_reg || 'N/A');
        row('Compliance',    companyInfo?.compliance_status === 1 ? 'VERIFIED ✓' : 'Pending');
        y += 4;

        // ── DMI Tier Certification ─────────────────────────────────────────────
        section('DMI TIER CERTIFICATION');
        row('Current Tier',  `${tier.label}`);
        row('Tier ID',       tier.id.toUpperCase());
        doc.setFontSize(8);
        doc.setFont('helvetica', 'italic');
        doc.setTextColor(100, 116, 139);
        const descLines = doc.splitTextToSize(tier.desc, W - margin * 2 - 4);
        doc.text(descLines, margin + 2, y);
        y += descLines.length * 5 + 6;

        // ── Financial Indicators ───────────────────────────────────────────────
        section('FINANCIAL INDICATORS');
        const fmt = (n: number) => `RM ${n.toLocaleString('en-MY', { minimumFractionDigits: 2 })}`;
        const pct = (n: number) => `${n}%`;
        row('Total Revenue',         fmt(analysisData?.totalRevenue || 0));
        row('Total Assets',          fmt(analysisData?.totalAssets || 0));
        row('Net Profit Margin',     pct(analysisData?.netProfitMargin || 0));
        row('Revenue Consistency',   pct(analysisData?.revenueConsistency || 0));
        row('Loan Readiness Score',  pct(analysisData?.loanReadinessScore || 0), true);
        row('Loan Approval Prob.',   pct(analysisData?.loanApprovalProbability || 0), true);
        y += 4;

        // ── DMI Progression Status ─────────────────────────────────────────────
        section('DMI PROGRESSION STATUS');
        TIERS.forEach((t, idx) => {
            const isAchieved = idx < activeTierIdx;
            const isCurrent  = idx === activeTierIdx;
            const [cr, cg, cb] = isCurrent ? [5,150,105] : isAchieved ? [71,85,105] : [203,213,225];
            doc.setFillColor(cr, cg, cb);
            doc.circle(margin + 3, y - 1, 2, 'F');
            doc.setFontSize(8.5);
            doc.setFont('helvetica', isCurrent ? 'bold' : 'normal');
            doc.setTextColor(15, 23, 42);
            const label = isCurrent ? `${t.label}  ← CURRENT` : isAchieved ? `${t.label}  ✓` : t.label;
            doc.text(label, margin + 8, y);
            doc.setTextColor(100,116,139);
            doc.setFontSize(7);
            doc.text(isCurrent ? 'Current Status' : isAchieved ? 'Achieved' : 'Locked', W - margin - 2, y, { align: 'right' });
            y += 7;
        });
        y += 4;

        // ── Footer ─────────────────────────────────────────────────────────────
        doc.setFillColor(15, 23, 42);
        doc.rect(0, 282, W, 15, 'F');
        doc.setTextColor(148, 163, 184);
        doc.setFontSize(7);
        doc.setFont('helvetica', 'normal');
        doc.text('Auto-generated by CtrlZ ADCB AI Engine  ·  Present to any ASEAN-compliant financial institution.', W / 2, 289, { align: 'center' });
        doc.text(`Ref: ${now.getTime()}`, W / 2, 293, { align: 'center' });

        doc.save(fileName);
    };

    if (loading) {
        return <div className="page-container" style={{ textAlign: 'center', padding: '10vh' }}>Verifying ASEAN Trust Ledger capabilities...</div>;
    }

    const currentTier = TIERS[activeTierIdx];

    return (
        <div className="page-container" style={{ maxWidth: '1000px', width: '100%', margin: '0 auto' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '2rem' }}>
                <div>
                    <h1 className="page-title" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        Regional Capability Passport <Globe size={20} color="#64748b" />
                    </h1>
                    <p className="page-subtitle">Pillar 4: Digital Maturity Index (DMI) and Cross-Border Trust Anchor</p>
                </div>
                <div style={{ padding: '0.5rem 1rem', background: '#ecfdf5', borderRadius: '8px', border: '1px solid #a7f3d0', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <ShieldCheck size={16} color="#059669" />
                    <span style={{ fontSize: '0.75rem', fontWeight: 600, color: '#065f46' }}>ASEAN Verified Node</span>
                </div>
            </div>

            {/* Premium Passport Card Display */}
            <motion.div 
                initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
                style={{
                    background: 'linear-gradient(135deg, #1e293b 0%, #0f172a 100%)',
                    borderRadius: '16px',
                    padding: '2.5rem',
                    color: 'white',
                    boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)',
                    marginBottom: '2.5rem',
                    position: 'relative',
                    overflow: 'hidden'
                }}
            >
                {/* Decorative background circle */}
                <div style={{ position: 'absolute', top: '-50px', right: '-50px', width: '250px', height: '250px', borderRadius: '50%', background: currentTier.color, opacity: 0.15, filter: 'blur(3xl)' }} />

                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', position: 'relative', zIndex: 1 }}>
                    <div>
                        <div style={{ fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.1em', color: '#94a3b8', marginBottom: '0.5rem' }}>Current DMI Verification</div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                            <span style={{ fontSize: '3rem' }}>{currentTier.icon}</span>
                            <div>
                                <h2 style={{ fontSize: '2rem', fontWeight: 700, margin: 0, background: `linear-gradient(90deg, #fff, ${currentTier.color})`, WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', filter: 'brightness(1.5)' }}>
                                    {currentTier.label}
                                </h2>
                                <div style={{ marginTop: '0.25rem' }}>
                                    <span style={{ margin: 0, color: '#94a3b8', fontSize: '0.875rem', fontWeight: 500 }}>{companyInfo?.name || 'Company Name Pending'}</span>
                                    {companyInfo?.business_reg && (
                                        <span style={{ fontSize: '0.75rem', color: '#64748b', marginLeft: '0.5rem', background: 'rgba(255,255,255,0.1)', padding: '0.1rem 0.5rem', borderRadius: '4px' }}>
                                            {companyInfo.business_reg}
                                        </span>
                                    )}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <div style={{ marginTop: '2rem', padding: '1.25rem', background: 'rgba(255,255,255,0.05)', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.1)', position: 'relative', zIndex: 1 }}>
                    <div style={{ fontSize: '0.875rem', fontWeight: 500, marginBottom: '0.5rem', color: '#cbd5e1' }}>What this means for you:</div>
                    <p style={{ fontSize: '0.8rem', color: '#94a3b8', margin: 0, lineHeight: 1.5 }}>
                        {currentTier.desc} 
                        {activeTierIdx > 2 && " You are mathematically proven to be a low-risk borrower, enabling frictionless, non-collateralized lending."}
                    </p>
                </div>
            </motion.div>

            {/* Progression Logic Timeline */}
            <div style={{ marginBottom: '2rem' }}>
                <h3 style={{ fontSize: '1rem', fontWeight: 600, color: '#1e293b', marginBottom: '1.5rem' }}>DMI Progression Path</h3>
                
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                    {TIERS.map((tier, idx) => {
                        const isUnlocked = idx <= activeTierIdx;
                        const isCurrent = idx === activeTierIdx;
                        const isNext = idx === activeTierIdx + 1;
                        
                        return (
                            <div key={tier.id} style={{
                                display: 'flex', 
                                alignItems: 'center', 
                                padding: '1.25rem', 
                                borderRadius: '12px', 
                                background: isUnlocked ? '#ffffff' : '#f8fafc',
                                border: '1px solid',
                                borderColor: isCurrent ? currentTier.color : (isUnlocked ? '#e2e8f0' : '#f1f5f9'),
                                opacity: isUnlocked ? 1 : 0.6,
                                transition: 'all 0.2s',
                                boxShadow: isCurrent ? '0 4px 6px -1px rgba(0, 0, 0, 0.05)' : 'none'
                            }}>
                                <div style={{ 
                                    width: 36, height: 36, 
                                    borderRadius: '50%', 
                                    background: isUnlocked ? tier.bg : '#f1f5f9',
                                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                                    marginRight: '1rem',
                                    fontSize: '1.2rem',
                                    opacity: isUnlocked ? 1 : 0.4
                                }}>
                                    {isUnlocked ? tier.icon : '🔒'}
                                </div>
                                <div style={{ flex: 1 }}>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                        <h4 style={{ margin: 0, fontSize: '0.9rem', fontWeight: 600, color: isUnlocked ? '#0f172a' : '#64748b' }}>{tier.label}</h4>
                                        {isCurrent && <span className="fintech-badge" style={{ background: currentTier.color, color: 'white', border: 'none' }}>Current Status</span>}
                                        {isNext && <span className="fintech-badge fintech-badge-neutral" style={{ fontSize: '0.6rem' }}>Next Goal</span>}
                                    </div>
                                    <p style={{ margin: '0.35rem 0 0', fontSize: '0.85rem', color: isUnlocked ? '#334155' : '#64748b', fontWeight: isUnlocked ? 500 : 400 }}>
                                        {isUnlocked ? '✓ ' : '🔒 '}{tier.checklist}
                                    </p>
                                </div>
                                <div style={{ marginLeft: '1rem' }}>
                                    {isUnlocked ? (
                                        <CheckCircle2 color="#10b981" size={20} />
                                    ) : (
                                        <div style={{ width: 20, height: 20, borderRadius: '50%', border: '2px solid #cbd5e1' }} />
                                    )}
                                </div>
                            </div>
                        );
                    })}
                </div>
            </div>

            <button onClick={generateBankExportProfile} className="fintech-btn fintech-btn-primary" style={{ width: '100%', height: '3rem', display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '0.5rem' }}>
                <TrendingUp size={16} /> Generate Verified Bank Export Profile
            </button>
        </div>
    );
};

export default PassportPage;
