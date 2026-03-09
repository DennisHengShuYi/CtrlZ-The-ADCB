
const ProgressBar = ({ label, value, max = 100, suffix = '%' }: any) => (
    <div style={{ marginBottom: '1.25rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.3rem' }}>
            <span style={{ fontSize: '0.8125rem', color: 'oklch(0.44 0 0)' }}>{label}</span>
            <span style={{ fontSize: '0.8125rem', fontWeight: 600, color: '#000' }}>{typeof value === 'number' ? value.toFixed(1) : value}{suffix}</span>
        </div>
        <div className="fintech-progress-bar">
            <div className="fintech-progress-fill" style={{ width: `${Math.min(100, (value / max) * 100)}%` }} />
        </div>
    </div>
);

export default ProgressBar;
