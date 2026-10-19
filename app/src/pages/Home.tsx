import { Download, FolderSearch, Play, RotateCcw, ShieldCheck, Wrench, AlertTriangle } from "lucide-react";
import { Card, InfoRow, PageHeader, Spinner, StatusPill } from "../components/ui";
import type { Controller } from "../lib/controller";

export default function Home({ app }: { app: Controller }) {
  const status = app.status;
  if (!status) {
    return <div className="flex h-64 items-center justify-center text-slate-500"><Spinner className="h-6 w-6" /></div>;
  }

  const state = status.state;
  const canInstall = state === "SUPPORTED_ORIGINAL" || state === "NOT_INSTALLED";
  const canUpdate = state === "ARABIC_UPDATE_AVAILABLE";
  const canRepair = state === "ARABIC_INSTALLED" || state === "BROKEN_INSTALL";
  const canRestore = status.backup.exists;
  const blocked = state === "UNKNOWN_MODIFIED_GAME";

  return (
    <div className="animate-rise">
      <PageHeader
        title="Wolfenstein: The Old Blood — العربية"
        subtitle="مدير التعريب العربي: التثبيت، الإصلاح، النسخ الاحتياطي والتحديثات."
        actions={<StatusPill state={state} pulse={app.busy === "status"} />}
      />

      <Card className="card-hover relative overflow-hidden">
        <div className="pointer-events-none absolute -left-24 -top-24 h-64 w-64 rounded-full bg-ember-500/10 blur-3xl" />
        <div className="relative flex flex-wrap items-start justify-between gap-6">
          <div className="max-w-xl">
            <div className="text-xs font-semibold tracking-widest text-ember-400">WOLFENSTEIN · THE OLD BLOOD</div>
            <h2 className="mt-2 text-xl font-bold text-white">التعريب العربي الكامل للنصوص المؤكدة</h2>
            <p className="mt-2 text-sm leading-7 text-slate-400">{status.message}</p>
          </div>
          <div className="grid min-w-[240px] grid-cols-2 gap-4">
            <InfoRow label="إصدار التعريب" value={status.installedVersion ?? "غير مثبت"} />
            <InfoRow label="أحدث إصدار" value={status.latestVersion} />
            <InfoRow label="حالة النسخة الاحتياطية" value={status.backup.exists ? (status.backup.verified ? "سليمة" : "تحتاج تحقق") : "غير موجودة"} />
            <InfoRow label="حالة التحديث" value={status.updateAvailable ? "متوفر" : "محدّث"} />
          </div>
        </div>

        <div className="relative mt-6 grid gap-3 border-t border-white/[0.06] pt-5 sm:grid-cols-3">
          <InfoRow label="مجلد اللعبة" value={status.game?.path ?? "—"} mono />
          <InfoRow label="مصدر الاكتشاف" value={status.game?.source === "steam" ? "Steam" : status.game?.source === "manual" ? "اختيار يدوي" : "—"} />
          <InfoRow label="ملف اللعبة التنفيذي" value={status.exeFound ? "موجود" : "غير موجود"} />
        </div>
      </Card>

      {blocked && (
        <div className="mt-4 flex items-start gap-3 rounded-xl border border-red-400/25 bg-red-500/[0.07] p-4 text-sm text-red-200 animate-rise">
          <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0" />
          <div>
            <div className="font-semibold">لن يتم تعديل ملفات غير معروفة تلقائيًا.</div>
            <p className="mt-1 leading-6 text-red-200/80">
              ملفات اللعبة لا تطابق أي إصدار مدعوم. قد تكون معدّلة بأداة أخرى أو إصدارًا مختلفًا.
              استعد النسخة الأصلية إن كانت لديك نسخة احتياطية، أو اختر مجلد اللعبة الصحيح.
            </p>
          </div>
        </div>
      )}

      <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <button className="btn-primary" disabled={!canInstall || !!app.busy} onClick={app.install}>
          {app.busy === "install" ? <Spinner /> : <Download className="h-4 w-4" />} تثبيت التعريب
        </button>
        <button className="btn-ghost" disabled={!canUpdate || !!app.busy} onClick={app.update}>
          {app.busy === "update" ? <Spinner /> : <Play className="h-4 w-4" />} تحديث
        </button>
        <button className="btn-ghost" disabled={!canRepair || !!app.busy} onClick={app.repair}>
          {app.busy === "repair" ? <Spinner /> : <Wrench className="h-4 w-4" />} إصلاح
        </button>
        <button className="btn-danger" disabled={!canRestore || !!app.busy} onClick={app.restore}>
          {app.busy === "restore" ? <Spinner /> : <RotateCcw className="h-4 w-4" />} استعادة الأصل
        </button>
      </div>

      <div className="mt-5 grid gap-3 sm:grid-cols-2">
        <button className="btn-ghost justify-start" disabled={!!app.busy} onClick={app.browse}>
          <FolderSearch className="h-4 w-4" /> اختيار مجلد اللعبة يدويًا
        </button>
        <button className="btn-ghost justify-start" disabled={!!app.busy} onClick={app.verifyBackup}>
          {app.busy === "verify" ? <Spinner /> : <ShieldCheck className="h-4 w-4" />} التحقق من النسخة الاحتياطية
        </button>
      </div>
    </div>
  );
}
