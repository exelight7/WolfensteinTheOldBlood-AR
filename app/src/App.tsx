import { useCallback, useEffect, useMemo, useState } from "react";
import { Home as HomeIcon, RefreshCw, HardDriveDownload, Info, ShieldCheck, Gamepad2 } from "lucide-react";
import { api, errorText } from "./lib/api";
import type { Controller, ToastKind } from "./lib/controller";
import type { AppInfo, Status, UpdateInfo } from "./lib/types";
import { Spinner, Toast } from "./components/ui";
import Home from "./pages/Home";
import Updates from "./pages/Updates";
import Backup from "./pages/Backup";
import About from "./pages/About";

type Page = "home" | "updates" | "backup" | "about";

const NAV: { id: Page; label: string; icon: typeof HomeIcon }[] = [
  { id: "home", label: "الرئيسية", icon: HomeIcon },
  { id: "updates", label: "التحديثات", icon: RefreshCw },
  { id: "backup", label: "النسخ الاحتياطي", icon: HardDriveDownload },
  { id: "about", label: "حول", icon: Info },
];

export default function App() {
  const [page, setPage] = useState<Page>("home");
  const [path, setPath] = useState<string | undefined>();
  const [status, setStatus] = useState<Status | null>(null);
  const [updates, setUpdates] = useState<UpdateInfo | null>(null);
  const [info, setInfo] = useState<AppInfo | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [toast, setToast] = useState<{ kind: ToastKind; message: string } | null>(null);

  const notify = useCallback((kind: ToastKind, message: string) => {
    setToast({ kind, message });
    window.setTimeout(() => setToast(null), 6000);
  }, []);

  const refresh = useCallback(async () => {
    setBusy("status");
    try {
      const next = await api.status(path);
      setStatus(next);
      if (next.game?.path) setPath(next.game.path);
    } catch (error) {
      notify("error", errorText(error));
    } finally {
      setBusy(null);
    }
  }, [path, notify]);

  useEffect(() => {
    let alive = true;
    (async () => {
      setBusy("status");
      try {
        const detected = await api.detectGame();
        const next = await api.status(detected?.path);
        if (!alive) return;
        setStatus(next);
        if (next.game?.path) setPath(next.game.path);
        const [u, i] = await Promise.all([api.checkUpdates().catch(() => null), api.appInfo()]);
        if (!alive) return;
        setUpdates(u);
        setInfo(i);
      } catch (error) {
        if (alive) notify("error", errorText(error));
      } finally {
        if (alive) setBusy(null);
      }
    })();
    return () => { alive = false; };
  }, [notify]);

  const busyLabel = useMemo(() => {
    if (busy === "install") return "جارٍ تثبيت التعريب…";
    if (busy === "update") return "جارٍ تحديث التعريب…";
    if (busy === "repair") return "جارٍ إصلاح التثبيت…";
    if (busy === "restore") return "جارٍ استعادة الملفات الأصلية…";
    if (busy === "verify") return "جارٍ التحقق من النسخة الاحتياطية…";
    if (busy === "updates") return "جارٍ التحقق من التحديثات…";
    return null;
  }, [busy]);

  const browse = useCallback(async () => {
    const selected = await api.browseFolder();
    if (!selected) return;
    setBusy("status");
    try {
      const game = await api.validateGame(selected);
      const next = await api.status(game.path);
      setStatus(next);
      setPath(game.path);
      notify("success", "تم التعرف على مجلد اللعبة.");
    } catch (error) {
      notify("error", errorText(error));
    } finally {
      setBusy(null);
    }
  }, [notify]);

  const run = useCallback(async (kind: "install" | "update" | "repair" | "restore", action: () => Promise<{ message: string }>) => {
    setBusy(kind);
    try {
      const result = await action();
      notify("success", result.message);
      const next = await api.status(path);
      setStatus(next);
    } catch (error) {
      notify("error", errorText(error));
    } finally {
      setBusy(null);
    }
  }, [path, notify]);

  const controller: Controller = {
    status,
    updates,
    info,
    busy,
    refresh,
    browse,
    install: () => run("install", () => api.install(path ?? "")),
    update: () => run("update", () => api.install(path ?? "")),
    repair: () => run("repair", () => api.repair(path ?? "")),
    restore: () => run("restore", () => api.restore(path ?? "")),
    verifyBackup: async () => {
      if (!path) return;
      setBusy("verify");
      try {
        const next = await api.verifyBackup(path);
        setStatus(next);
        notify(next.backup.verified ? "success" : "error", next.backup.verified ? "النسخة الاحتياطية سليمة." : "النسخة الاحتياطية غير مطابقة.");
      } catch (error) {
        notify("error", errorText(error));
      } finally {
        setBusy(null);
      }
    },
    checkUpdates: async () => {
      setBusy("updates");
      try {
        const next = await api.checkUpdates();
        setUpdates(next);
        notify("info", next.dataUpdateAvailable || next.appUpdateAvailable ? "يتوفر تحديث." : "كل شيء محدّث.");
      } catch (error) {
        notify("error", errorText(error));
      } finally {
        setBusy(null);
      }
    },
    openUrl: (url: string) => {
      api.openUrl(url).catch((error) => notify("error", errorText(error)));
    },
    notify,
  };

  return (
    <div className="flex min-h-screen">
      <aside className="sticky top-0 hidden h-screen w-64 shrink-0 flex-col border-e border-white/[0.06] bg-ink-900/70 p-4 backdrop-blur lg:flex">
        <div className="flex items-center gap-3 px-2 py-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-ember-400/25 bg-ember-500/10 text-ember-400">
            <Gamepad2 className="h-5 w-5" />
          </div>
          <div>
            <div className="text-sm font-bold text-white">WOLFENSTEIN</div>
            <div className="text-[10px] tracking-[0.2em] text-slate-500">ARABIC MANAGER</div>
          </div>
        </div>

        <nav className="mt-6 space-y-1">
          {NAV.map(({ id, label, icon: Icon }) => (
            <button key={id} onClick={() => setPage(id)} className={`nav-item ${page === id ? "nav-item-active" : ""}`}>
              <Icon className="h-4 w-4" />
              <span>{label}</span>
            </button>
          ))}
        </nav>

        <div className="mt-auto rounded-xl border border-white/[0.06] bg-white/[0.02] p-3">
          <div className="flex items-center gap-2 text-xs text-slate-400">
            <ShieldCheck className="h-4 w-4 text-emerald-400" />
            <span>الإصدار {info?.appVersion ?? "1.0.1"}</span>
          </div>
          <div className="mt-2 flex items-center gap-2 text-[11px] text-slate-500">
            {busy ? <><Spinner className="h-3 w-3" /> {busyLabel}</> : <><span className="h-1.5 w-1.5 rounded-full bg-emerald-400" /> جاهز</>}
          </div>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between gap-3 border-b border-white/[0.06] px-4 py-3 lg:hidden">
          <div className="flex items-center gap-2 text-sm font-bold text-white"><Gamepad2 className="h-4 w-4 text-ember-400" /> مدير التعريب</div>
          <nav className="flex gap-1">
            {NAV.map(({ id, icon: Icon }) => (
              <button key={id} onClick={() => setPage(id)} aria-label={id} className={`rounded-lg p-2 ${page === id ? "bg-white/10 text-white" : "text-slate-400"}`}>
                <Icon className="h-4 w-4" />
              </button>
            ))}
          </nav>
        </header>

        <main className="mx-auto w-full max-w-5xl flex-1 p-5 lg:p-8">
          {page === "home" && <Home app={controller} />}
          {page === "updates" && <Updates app={controller} />}
          {page === "backup" && <Backup app={controller} />}
          {page === "about" && <About app={controller} />}
        </main>
      </div>

      {toast && <Toast kind={toast.kind} message={toast.message} onClose={() => setToast(null)} />}
    </div>
  );
}
