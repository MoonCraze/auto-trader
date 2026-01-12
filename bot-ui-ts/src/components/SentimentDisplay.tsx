import React, { useState } from 'react';
import { SentimentData } from '../types';

interface SentimentDisplayProps {
    sentimentData: SentimentData;
    mentionCount: number | null;
}

const SentimentDisplay: React.FC<SentimentDisplayProps> = ({ sentimentData, mentionCount }) => {
    const [showTooltip, setShowTooltip] = useState(false);
    const [showTweets, setShowTweets] = useState(false);

    const { score, twitter_details, sample_texts } = sentimentData;

    // Calculate percentages for the bar
    const positiveCount = twitter_details?.pos || 0;
    const negativeCount = twitter_details?.neg || 0;
    const total = twitter_details?.total || positiveCount + negativeCount || 1;
    const neutralCount = total - positiveCount - negativeCount;

    const positivePercent = (positiveCount / total) * 100;
    const neutralPercent = (neutralCount / total) * 100;
    const negativePercent = (negativeCount / total) * 100;

    const getSentimentColor = (score: number) => {
        if (score > 75) return 'text-green-400';
        if (score > 60) return 'text-yellow-400';
        return 'text-red-400';
    };

    const getSentimentBadgeColor = (sentiment: string) => {
        switch (sentiment) {
            case 'positive':
                return 'bg-green-500/20 text-green-400 border-green-500/30';
            case 'negative':
                return 'bg-red-500/20 text-red-400 border-red-500/30';
            case 'neutral':
            default:
                return 'bg-gray-500/20 text-gray-400 border-gray-500/30';
        }
    };

    return (
        <div className="text-xs mt-2 pt-2 border-t border-gray-700/50">
            {/* Sentiment Score Header */}
            <div className="flex justify-between items-center mb-2">
                <span className="text-gray-400">Sentiment:</span>
                <div className="flex items-center gap-2">
                    <span className={`font-mono font-semibold ${getSentimentColor(score)}`}>
                        {score.toFixed(1)}
                    </span>
                    {mentionCount !== null && (
                        <span className="text-gray-500 text-[10px]">
                            ({mentionCount} mentions)
                        </span>
                    )}
                </div>
            </div>

            {/* Sentiment Bar with Hover Tooltip */}
            {twitter_details && (
                <div className="relative">
                    <div
                        className="h-3 rounded-full overflow-hidden flex cursor-help bg-gray-800"
                        onMouseEnter={() => setShowTooltip(true)}
                        onMouseLeave={() => setShowTooltip(false)}
                    >
                        {/* Positive segment */}
                        {positivePercent > 0 && (
                            <div
                                className="bg-green-500 transition-all"
                                style={{ width: `${positivePercent}%` }}
                            />
                        )}
                        {/* Neutral segment */}
                        {neutralPercent > 0 && (
                            <div
                                className="bg-gray-500 transition-all"
                                style={{ width: `${neutralPercent}%` }}
                            />
                        )}
                        {/* Negative segment */}
                        {negativePercent > 0 && (
                            <div
                                className="bg-red-500 transition-all"
                                style={{ width: `${negativePercent}%` }}
                            />
                        )}
                    </div>

                    {/* Hover Tooltip */}
                    {showTooltip && (
                        <div className="absolute z-50 bottom-full left-1/2 transform -translate-x-1/2 mb-2 bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 shadow-lg min-w-[200px]">
                            <div className="space-y-1">
                                <div className="flex justify-between items-center">
                                    <span className="flex items-center gap-1">
                                        <span className="w-2 h-2 rounded-full bg-green-500"></span>
                                        <span className="text-green-400">Positive:</span>
                                    </span>
                                    <span className="text-white font-semibold">
                                        {positiveCount} ({twitter_details.pos_pct.toFixed(2)}%)
                                    </span>
                                </div>
                                <div className="flex justify-between items-center">
                                    <span className="flex items-center gap-1">
                                        <span className="w-2 h-2 rounded-full bg-gray-500"></span>
                                        <span className="text-gray-400">Neutral:</span>
                                    </span>
                                    <span className="text-white font-semibold">
                                        {neutralCount} ({neutralPercent.toFixed(2)}%)
                                    </span>
                                </div>
                                <div className="flex justify-between items-center">
                                    <span className="flex items-center gap-1">
                                        <span className="w-2 h-2 rounded-full bg-red-500"></span>
                                        <span className="text-red-400">Negative:</span>
                                    </span>
                                    <span className="text-white font-semibold">
                                        {negativeCount} ({twitter_details.neg_pct.toFixed(2)}%)
                                    </span>
                                </div>
                            </div>
                            {/* Tooltip arrow */}
                            <div className="absolute top-full left-1/2 transform -translate-x-1/2 w-0 h-0 border-l-4 border-r-4 border-t-4 border-transparent border-t-gray-700"></div>
                        </div>
                    )}
                </div>
            )}

            {/* View Tweets Button */}
            {sample_texts && sample_texts.length > 0 && (
                <div className="mt-2">
                    <button
                        onClick={() => setShowTweets(!showTweets)}
                        className="text-blue-400 hover:text-blue-300 text-[10px] flex items-center gap-1 transition-colors"
                    >
                        <span>{showTweets ? '▼' : '▶'}</span>
                        <span>{showTweets ? 'Hide' : 'View'} Tweets ({sample_texts.length})</span>
                    </button>

                    {/* Tweets List */}
                    {showTweets && (
                        <div className="mt-2 space-y-2 max-h-[300px] overflow-y-auto pr-1 themed-scrollbar">
                            {sample_texts.map((tweet, index) => (
                                <div
                                    key={index}
                                    className="bg-gray-900/50 rounded p-2 border border-gray-700/50"
                                >
                                    <div className="flex justify-between items-start gap-2 mb-1">
                                        <span className="text-[9px] text-gray-500">
                                            Tweet {index + 1}
                                        </span>
                                        <span
                                            className={`text-[9px] px-1.5 py-0.5 rounded border capitalize ${getSentimentBadgeColor(
                                                tweet.sentiment
                                            )}`}
                                        >
                                            {tweet.sentiment}
                                        </span>
                                    </div>
                                    <p className="text-[10px] text-gray-300 leading-relaxed whitespace-pre-wrap">
                                        {tweet.text}
                                    </p>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}
        </div>
    );
};

export default SentimentDisplay;
