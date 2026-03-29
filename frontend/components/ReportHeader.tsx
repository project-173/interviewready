export const ReportHeader: React.FC<{
  title: string;
  summary: string;
  score?: number | string | null;
  scoreLabel?: string;
}> = ({ title, summary, score, scoreLabel = "Score" }) => {
  const hasScore = score !== null && score !== undefined && score !== "";
  return (
    <div className="flex items-start justify-between border-b border-slate-100 pb-4 gap-4">
      <div className="min-w-0">
        <h3 className="text-lg font-semibold text-slate-900 mb-1">{title}</h3>
        <p className="text-[12px] text-slate-500 leading-relaxed line-clamp-3">
          "{summary}"
        </p>
      </div>
      {hasScore && (
        <div className="text-right flex-none">
          <div className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">
            {scoreLabel}
          </div>
          <div className="text-2xl font-bold text-slate-900">{score}</div>
        </div>
      )}
    </div>
  );
};
