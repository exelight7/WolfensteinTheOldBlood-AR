import { HardDriveDownload, RotateCcw, ShieldCheck, Wrench, ShieldAlert } from "lucide-react";
import { Card, InfoRow, PageHeader, Spinner, StatusPill } from "../components/ui";
import type { Controller } from "../lib/controller";

export default function Backup({ app }: { app: Controller }) {
  const status = app.status;
  if (!status) return <div className="h-64" />;
  const b = status.backup;

  return (
    <div className="animate-rise">
      <PageHeader
        title="النسخ الاحتياطي والإصلاح"
        subtitle="نسخة أصلية موثّقة ببصمات SHA-256، وإصلاح آمن دون لمس الملفات غير المعروفة."
        actions={<StatusPill state={status.state} />}
      />

      <div className="grid gap-4 lg:grid-cols-2">
        <Card className="card-hover">
          <div className="flex items-center gap-3">
            <div className={`rounded-xl p-2.5 ${b.exists && b.verified ? "bg-emerald-500/10 text-emerald-300" : "bg-white/[0.04] text-slate-400"}`}>
              {b.exists && b.verified ? <ShieldCheck className="h-5 w-5" /> : <ShieldAlert className="h-5 w-5" />}
            </div>
            <div>
              <h3 className="font-semibold text-white">حالة النسخة الاحتياطية</h3>
              <p className="text-xs text-slate-400">
                {!b.exists ? "لا توجد نسخة احتياطية بعد." : b.verified ? "النسخة سليمة ومطابقة للبصمات." : "النسخة موجودة لكنها تحتاج إلى تحقق."}
              </p>
            </div>
          </div>
          <div className="mt-5 grid grid-cols-2 gap-4">
            <InfoRow label="موجودة" value={b.exists ? "نعم" : "لا"} />
            <InfoRow label="متحقَّق منها" value={b.verified ? "نعم" : "لا"} />
            <InfoRow label="التاريخ" value={b.createdAt ?? "—"} />
            <InfoRow label="المسار" value={b.path ?? "—"} mono />
          </div>
          <div className="mt-5 flex flex-wrap gap-2">
            <button className="btn-ghost" onClick={app.verifyBackup} disabled={!b.exists || !!app.busy}>
              {app.busy === "verify" ? <Spinner /> : <ShieldCheck className="h-4 w-4" />} تحقق
            </button>
            <button className="btn-ghost" onClick={app.repair} disabled={!!app.busy || status.state === "GAME_NOT_FOUND"}>
              {app.busy === "repair" ? <Spinner /> : <Wrench className="h-4 w-4" />} إصلاح
            </button>
            <button className="btn-danger" onClick={app.restore} disabled={!b.exists || !!app.busy}>
              {app.busy === "restore" ? <Spinner /> : <RotateCcw className="h-4 w-4" />} استعادة الأصل
            </button>
          </div>
        </Card>

        <Card>
          <div className="flex items-center gap-3">
            <div className="rounded-xl bg-white/[0.04] p-2.5 text-slate-300"><HardDriveDownload className="h-5 w-5" /></div>
            <h3 className="font-semibold text-white">كيف تعمل العملية؟</h3>
          </div>
          <ol className="mt-4 space-y-3 text-sm leading-6 text-slate-400">
            <li><span className="font-semibold text-slate-200">1.</span> التحقق من إغلاق اللعبة ومن بصمات الملفات الأصلية.</li>
            <li><span className="font-semibold text-slate-200">2.</span> إنشاء نسخة احتياطية موثّقة قبل أي تعديل.</li>
            <li><span className="font-semibold text-slate-200">3.</span> تجهيز الملفات الجديدة والتحقق من بصماتها.</li>
            <li><span className="font-semibold text-slate-200">4.</span> الاستبدال الذرّي مع تراجع تلقائي عند أي فشل.</li>
            <li><span className="font-semibold text-slate-200">5.</span> التحقق النهائي من الملفات المثبتة.</li>
          </ol>
          <p className="mt-4 rounded-lg border border-white/[0.06] bg-white/[0.02] p-3 text-xs leading-6 text-slate-500">
            لا تُستبدل النسخة الاحتياطية الأصلية أبدًا بملفات معدّلة. الاستعادة تتحقق من البصمات قبل الكتابة.
          </p>
        </Card>
      </div>
    </div>
  );
}
