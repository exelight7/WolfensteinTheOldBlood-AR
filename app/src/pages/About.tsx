import { Bug, ExternalLink, Github, Scale, ShieldCheck } from "lucide-react";
import { Card, InfoRow, PageHeader } from "../components/ui";
import type { Controller } from "../lib/controller";

export default function About({ app }: { app: Controller }) {
  const info = app.info;
  return (
    <div className="animate-rise">
      <PageHeader title="حول التطبيق" subtitle="معلومات الإصدار والترخيص والاعتمادات." />

      <div className="grid gap-4 lg:grid-cols-2">
        <Card className="card-hover">
          <div className="flex items-center gap-4">
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl border border-ember-400/20 bg-ember-500/10 text-lg font-black text-ember-400">
              AR
            </div>
            <div>
              <h3 className="text-lg font-bold text-white">Wolfenstein: The Old Blood — العربية</h3>
              <p className="text-xs text-slate-400">مدير التعريب · إصدار {info?.appVersion ?? "1.0.0"}</p>
            </div>
          </div>
          <div className="mt-5 grid grid-cols-2 gap-4">
            <InfoRow label="إصدار التطبيق" value={info?.appVersion ?? "1.0.0"} />
            <InfoRow label="إصدار التعريب" value={info?.localizationVersion ?? "1.0.0"} />
            <InfoRow label="الترخيص" value={info?.license ?? "MIT"} />
            <InfoRow label="المعرّف" value="com.exelight7.wtob.arabic" mono />
          </div>
        </Card>

        <Card>
          <h3 className="font-semibold text-white">روابط</h3>
          <div className="mt-4 space-y-2">
            <button className="btn-ghost w-full justify-between" onClick={() => app.openUrl(info?.github ?? "https://github.com/exelight7/WolfensteinTheOldBlood-AR")}>
              <span className="flex items-center gap-2"><Github className="h-4 w-4" /> مستودع GitHub</span>
              <ExternalLink className="h-4 w-4 opacity-60" />
            </button>
            <button className="btn-ghost w-full justify-between" onClick={() => app.openUrl(info?.issueUrl ?? "https://github.com/exelight7/WolfensteinTheOldBlood-AR/issues")}>
              <span className="flex items-center gap-2"><Bug className="h-4 w-4" /> الإبلاغ عن مشكلة</span>
              <ExternalLink className="h-4 w-4 opacity-60" />
            </button>
            <button className="btn-ghost w-full justify-between" onClick={() => app.openUrl("https://github.com/exelight7/WolfensteinTheOldBlood-AR/blob/main/LICENSE")}>
              <span className="flex items-center gap-2"><Scale className="h-4 w-4" /> نص الترخيص MIT</span>
              <ExternalLink className="h-4 w-4 opacity-60" />
            </button>
          </div>
        </Card>

        <Card className="lg:col-span-2">
          <div className="flex items-center gap-2 text-sm font-semibold text-white"><ShieldCheck className="h-4 w-4 text-emerald-400" /> اعتمادات وإخلاء مسؤولية</div>
          <ul className="mt-3 space-y-2 text-sm leading-7 text-slate-400">
            <li>خط IBM Plex Sans Arabic مرخّص بموجب SIL Open Font License؛ تُحفظ شروط الترخيص والاعتماد.</li>
            <li>Wolfenstein: The Old Blood وكل أصولها ملك لأصحاب الحقوق (MachineGames / Bethesda) ولا تُوزّع هنا.</li>
            <li>هذا تعريب غير رسمي من المجتمع ويتطلب نسخة أصلية مرخّصة من اللعبة.</li>
            <li>شكر خاص لكل من ساهم في المراجعة اللغوية واختبار اللعبة.</li>
          </ul>
        </Card>
      </div>
    </div>
  );
}
