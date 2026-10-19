import { CheckCircle2, ExternalLink, RefreshCw, ArrowUpCircle } from "lucide-react";
import { Card, InfoRow, PageHeader, Spinner } from "../components/ui";
import type { Controller } from "../lib/controller";

export default function Updates({ app }: { app: Controller }) {
  const u = app.updates;
  return (
    <div className="animate-rise">
      <PageHeader
        title="التحديثات"
        subtitle="تحديثات التطبيق وبيانات التعريب من إصدارات GitHub الرسمية."
        actions={
          <button className="btn-ghost" onClick={app.checkUpdates} disabled={!!app.busy}>
            {app.busy === "updates" ? <Spinner /> : <RefreshCw className="h-4 w-4" />} التحقق من التحديثات
          </button>
        }
      />

      {!u ? (
        <Card><p className="text-sm text-slate-400">لم يتم التحقق بعد. اضغط «التحقق من التحديثات».</p></Card>
      ) : (
        <div className="grid gap-4 lg:grid-cols-2">
          <Card className="card-hover">
            <div className="flex items-center justify-between">
              <h3 className="font-semibold text-white">تطبيق المدير</h3>
              {u.appUpdateAvailable ? <span className="text-xs font-semibold text-sky-300">تحديث متوفر</span> : <CheckCircle2 className="h-4 w-4 text-emerald-400" />}
            </div>
            <div className="mt-4 grid grid-cols-2 gap-4">
              <InfoRow label="الحالي" value={u.appVersion} />
              <InfoRow label="الأحدث" value={u.latestAppVersion} />
            </div>
          </Card>

          <Card className="card-hover">
            <div className="flex items-center justify-between">
              <h3 className="font-semibold text-white">بيانات التعريب</h3>
              {u.dataUpdateAvailable ? <span className="text-xs font-semibold text-sky-300">تحديث متوفر</span> : <CheckCircle2 className="h-4 w-4 text-emerald-400" />}
            </div>
            <div className="mt-4 grid grid-cols-2 gap-4">
              <InfoRow label="المثبت" value={u.localizationVersion} />
              <InfoRow label="الأحدث" value={u.latestLocalizationVersion} />
            </div>
          </Card>

          <Card className="lg:col-span-2">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <div className="label">ملاحظات الإصدار</div>
                <div className="mt-1 text-sm text-slate-300">
                  عرض سجل التغييرات الكامل وإصدار GitHub الرسمي.
                </div>
              </div>
              <div className="flex gap-2">
                <button className="btn-ghost" onClick={() => app.openUrl(u.changelogUrl)}>
                  <ExternalLink className="h-4 w-4" /> سجل التغييرات
                </button>
                <button className="btn-ghost" onClick={() => app.openUrl(u.releaseUrl)}>
                  <ArrowUpCircle className="h-4 w-4" /> صفحة الإصدار
                </button>
              </div>
            </div>
          </Card>
        </div>
      )}

      <p className="mt-4 text-xs leading-6 text-slate-500">
        يتم التحقق من رقم الإصدار وقائمة الملفات وبصمة SHA-256 قبل تثبيت أي حزمة. لا يتم تجاوز التحقق أبدًا.
      </p>
    </div>
  );
}
