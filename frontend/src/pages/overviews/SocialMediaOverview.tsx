// frontend/src/pages/overviews/SocialMediaOverview.tsx
import { useState, useEffect } from "react";
import { useUser } from "@clerk/clerk-react";
import { useApiFetch } from "../../hooks/useApiFetch";
import {
    LineChart,
    Line,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
} from "recharts";
import Slider from "react-slick";
import "slick-carousel/slick/slick.css";
import "slick-carousel/slick/slick-theme.css";

// Types (adjust based on your actual data)
interface Post {
    id: string;
    caption: string;
    likes: number;
    comments: Comment[];
}

interface Comment {
    id: string;
    username: string;
    text: string;
    sentiment?: string;
    ai_reply?: string;
}

interface EngagementPoint {
    date: string;
    engagement: number;
}

interface Product {
    id: string;
    name: string;
    inventory: number;
    threshold: number;
    image?: string;  // optional image/emoji - we won't use it
    score: number;
    inquiries: number;
}

export default function SocialMediaOverview() {
    const { user } = useUser();
    const apiFetch = useApiFetch();

    const [posts, setPosts] = useState<Post[]>([]);
    const [engagementData, setEngagementData] = useState<EngagementPoint[]>([]);
    const [topProducts, setTopProducts] = useState<Product[]>([]);
    const [mostEnquiredProduct, setMostEnquiredProduct] = useState<{ name: string; inquiries: number } | null>(null);

    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const [selectedComment, setSelectedComment] = useState<{ id: string; reply: string } | null>(null);
    const [generatingFor, setGeneratingFor] = useState<string | null>(null);

    const displayName =
        user?.firstName ??
        user?.emailAddresses[0]?.emailAddress?.split("@")[0] ??
        "there";

    const hour = new Date().getHours();
    const greeting =
        hour < 12 ? "Good morning" : hour < 18 ? "Good afternoon" : "Good evening";

    const [groupBy, setGroupBy] = useState<"day" | "week" | "month" | "quarter" | "year">("day");

    useEffect(() => {
        fetchData();
    }, [groupBy]);

    const fetchData = async () => {
        setLoading(true);
        setError(null);
        try {
            const [feedRes, engagementRes, topProductsRes, mostEnquiredRes] = await Promise.allSettled([
                apiFetch("/api/instagram/feed"),
                apiFetch(`/api/instagram/engagement-over-time?group_by=${groupBy}`),
                apiFetch("/api/products/top?limit=5"),
                apiFetch("/api/products/most-enquired"),
            ]);

            if (feedRes.status === "fulfilled") setPosts(feedRes.value || []);
            if (engagementRes.status === "fulfilled") setEngagementData(engagementRes.value || []);
            if (topProductsRes.status === "fulfilled") setTopProducts(topProductsRes.value || []);
            if (mostEnquiredRes.status === "fulfilled") setMostEnquiredProduct(mostEnquiredRes.value);
        } catch (err) {
            setError("Failed to load social media data");
        } finally {
            setLoading(false);
        }
    };

    const handleGenerateReply = async (commentId: string) => {
        setGeneratingFor(commentId);
        try {
            const res = await apiFetch(`/api/instagram/comment/${commentId}/analyze`, {
                method: "POST",
            });
            setSelectedComment({ id: commentId, reply: res.suggested_reply });
            setPosts(prevPosts =>
                prevPosts.map(post => ({
                    ...post,
                    comments: post.comments.map(c =>
                        c.id === commentId ? { ...c, ai_reply: res.suggested_reply } : c
                    )
                }))
            );
        } catch (error) {
            console.error("Failed to generate reply", error);
        } finally {
            setGeneratingFor(null);
        }
    };

    // Stats
    const totalLikes = posts.reduce((sum, p) => sum + (p.likes || 0), 0);
    const totalFollowers = 1234; // mock
    const mostInteractedPost = posts.reduce(
        (max, p) => {
            const score = (p.likes || 0) + (p.comments?.length || 0) * 2;
            return score > (max.score || 0) ? { caption: p.caption, score } : max;
        },
        { caption: "None", score: 0 }
    );

    const allComments = posts.flatMap(post => post.comments.map(c => ({ ...c, postCaption: post.caption })));

    // Carousel settings: no infinite loop, show ranking
    const sliderSettings = {
        dots: true,
        infinite: false,
        speed: 500,
        slidesToShow: 3,
        slidesToScroll: 1,
        responsive: [
            { breakpoint: 1024, settings: { slidesToShow: 2 } },
            { breakpoint: 600, settings: { slidesToShow: 1 } }
        ]
    };

    if (loading) {
        return (
            <div className="page-container flex justify-center items-center min-h-[400px]">
                <div className="spinner" />
            </div>
        );
    }

    if (error) {
        return (
            <div className="page-container">
                <div className="bg-destructive/10 border border-destructive text-destructive rounded-lg p-4">
                    {error}
                </div>
            </div>
        );
    }

    return (
        <div className="page-container flex flex-col gap-5"> {/* Flex layout with gap-5 for reliable spacing between containers */}
            <div className="page-header">
                <div>
                    <h1 className="page-title">
                        {greeting}, {displayName} 👋
                    </h1>
                    <p className="page-subtitle">
                        Here's what's happening with your social media today.
                    </p>
                </div>
            </div>

            {/* Stats Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                <div className="overview-stat-card">
                    <div className="stat-card-header">
                        <div className="stat-icon-wrapper">❤️</div>
                    </div>
                    <div className="stat-card-body">
                        <div className="stat-value">{totalLikes.toLocaleString()}</div>
                        <div className="stat-label">Total Likes</div>
                    </div>
                </div>
                <div className="overview-stat-card">
                    <div className="stat-card-header">
                        <div className="stat-icon-wrapper">👥</div>
                    </div>
                    <div className="stat-card-body">
                        <div className="stat-value">{totalFollowers.toLocaleString()}</div>
                        <div className="stat-label">Total Followers</div>
                    </div>
                </div>
                <div className="overview-stat-card">
                    <div className="stat-card-header">
                        <div className="stat-icon-wrapper">🔥</div>
                    </div>
                    <div className="stat-card-body">
                        <div className="stat-value truncate" title={mostInteractedPost.caption}>
                            {mostInteractedPost.caption}
                        </div>
                        <div className="stat-label">Most Interacted Post with Score: {mostInteractedPost.score}</div>
                    </div>
                </div>
            </div>

            {/* Engagement Chart */}
            <div className="bg-white border border-border rounded-lg p-6 shadow-sm">
                <div className="flex justify-between items-center mb-6 px-1">
                    <h3 className="text-sm font-semibold text-foreground">Engagement Over Time</h3>
                    <select
                        value={groupBy}
                        onChange={(e) => setGroupBy(e.target.value as any)}
                        className="border border-input rounded px-3 py-1 text-xs bg-background"
                    >
                        <option value="day">Daily</option>
                        <option value="week">Weekly</option>
                        <option value="month">Monthly</option>
                        <option value="quarter">Quarterly</option>
                        <option value="year">Yearly</option>
                    </select>
                </div>
                <div className="h-96 w-full -ml-4 pr-4"> {/* Slight negative margin to offset Recharts default padding */}
                    <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={engagementData} margin={{ top: 10, right: 10, left: 10, bottom: 0 }}>
                            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                            <XAxis dataKey="date" stroke="var(--muted-foreground)" fontSize={12} />
                            <YAxis stroke="var(--muted-foreground)" fontSize={12} />
                            <Tooltip
                                contentStyle={{
                                    backgroundColor: 'var(--background)',
                                    border: '1px solid var(--border)',
                                    borderRadius: '8px',
                                    fontSize: '12px'
                                }}
                            />
                            <Line type="monotone" dataKey="engagement" stroke="var(--foreground)" strokeWidth={2} />
                        </LineChart>
                    </ResponsiveContainer>
                </div>
            </div>

            {/* Top Products Carousel with Ranking */}
            {topProducts.length > 0 && (
                <div className="bg-white border border-border rounded-lg p-6 shadow-sm">
                    <div className="px-1">
                        <h3 className="text-sm font-semibold text-foreground mb-4">Top Products by Engagement</h3>
                        <Slider {...sliderSettings}>
                            {topProducts.map((product, index) => (
                                <div key={product.id} className="px-2">
                                    <div className="border border-border rounded-lg p-4 flex flex-col items-center text-center h-full relative">
                                        {/* Ranking badge */}
                                        <div className="absolute top-2 left-2 bg-foreground text-background text-xs font-bold w-6 h-6 rounded-full flex items-center justify-center">
                                            {index + 1}
                                        </div>
                                        <div className="mt-4 mb-2 w-12 h-12 bg-muted rounded-full flex items-center justify-center text-2xl">
                                            {product.image || '📦'}
                                        </div>
                                        <h4 className="text-sm font-medium text-foreground">{product.name}</h4>
                                        <p className="text-xs text-muted-foreground mt-1">Score: {product.score}</p>
                                        <p className="text-xs text-muted-foreground">Inventory: {product.inventory}</p>
                                        {product.inventory < product.threshold && (
                                            <span className="badge-warning status-badge mt-2">Low stock</span>
                                        )}
                                    </div>
                                </div>
                            ))}
                        </Slider>
                    </div>
                </div>
            )}

            {/* Most Enquired Product Card - Prominent */}
            {mostEnquiredProduct && (
                <div className="bg-white border border-border rounded-lg p-6 shadow-sm">
                    <div className="px-1">
                        <h3 className="text-sm font-semibold text-foreground mb-3">📞 Most Enquired Product</h3>
                        <div className="flex items-center gap-4 mt-2">
                            <div className="w-12 h-12 bg-muted rounded-full flex items-center justify-center text-2xl border border-border">
                                🏆
                            </div>
                            <div>
                                <p className="text-lg font-bold text-foreground">{mostEnquiredProduct.name}</p>
                                <p className="text-sm text-muted-foreground">{mostEnquiredProduct.inquiries} WhatsApp inquiries</p>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* Instagram Comments Table */}
            <div className="table-container shadow-sm p-6 bg-white border border-border rounded-lg">
                <div className="px-1 pb-4">
                    <h3 className="text-sm font-semibold text-foreground">Recent Comments</h3>
                </div>
                <div className="overflow-x-auto rounded-lg border border-border">
                    <table className="data-table">
                        <thead>
                            <tr>
                                <th>User</th>
                                <th>Comment</th>
                                <th>Sentiment</th>
                                <th>AI Reply</th>
                                <th>Action</th>
                            </tr>
                        </thead>
                        <tbody>
                            {allComments.map((comment) => (
                                <tr key={comment.id}>
                                    <td className="cell-bold">{comment.username}</td>
                                    <td className="cell-truncate max-w-xs" title={comment.text}>
                                        {comment.text}
                                    </td>
                                    <td>
                                        {comment.sentiment ? (
                                            <span className={`status-badge ${comment.sentiment === 'positive' ? 'badge-success' :
                                                comment.sentiment === 'negative' ? 'badge-warning' :
                                                    'badge-default'
                                                }`}>
                                                {comment.sentiment}
                                            </span>
                                        ) : (
                                            <span className="text-muted-foreground text-xs">—</span>
                                        )}
                                    </td>
                                    <td className="cell-truncate max-w-xs">
                                        {comment.ai_reply ? (
                                            <span className="badge-info status-badge">
                                                🤖 {comment.ai_reply.substring(0, 30)}...
                                            </span>
                                        ) : (
                                            <span className="text-muted-foreground text-xs">—</span>
                                        )}
                                    </td>
                                    <td>
                                        <button
                                            onClick={() => handleGenerateReply(comment.id)}
                                            disabled={generatingFor === comment.id}
                                            className="btn-primary btn-sm"
                                        >
                                            {generatingFor === comment.id ? (
                                                <span className="spinner w-3 h-3 border-2" />
                                            ) : (
                                                "Generate"
                                            )}
                                        </button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
                {selectedComment && (
                    <div className="p-4 border-t border-border bg-muted/20">
                        <p className="text-xs font-medium text-foreground mb-1">Generated Reply:</p>
                        <p className="text-sm text-muted-foreground">{selectedComment.reply}</p>
                        <button
                            onClick={() => setSelectedComment(null)}
                            className="btn-icon btn-sm mt-2"
                        >
                            Dismiss
                        </button>
                    </div>
                )}
            </div>
        </div>
    );
}