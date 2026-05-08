"use client";

import { useState } from "react";
import {
  Shield, RefreshCw, Database, FileText, CheckCircle2,
  AlertTriangle, Activity, Globe, Zap, Clock, Server,
  Play, RotateCcw, Search, List, ArrowLeft, ChevronRight,
  Wifi, HardDrive, Cpu, TrendingUp
} from "lucide-react";

const SOURCES = [
  { name: "Radio Okapi",         url: "radiookapi.net",         status: "ok",      articles: 842, lastCrawl: "il y a 12 min" },
  { name: "ACP",                 url: "acp.cd",                 status: "ok",      articles: 431, lastCrawl: "il y a 14 min" },
  { name: "7sur7.cd",            url: "7sur7.cd",               status: "ok",      articles: 318, lastCrawl: "il y a 18 min" },
  { name: "actualite.cd",        url: "actualite.cd",           status: "warning", articles: 204, lastCrawl: "il y a 2 h" },
  { name: "Congo Indépendant",   url: "congoindependant.com",   status: "ok",      articles: 156, lastCrawl: "il y a 22 min" },
  { name: "RFI Afrique",         url: "rfi.fr",                 status: "ok",      articles: 290, lastCrawl: "il y a 9 min" },
];

const LOGS = [
  { time: "14:32:01", level: "info",    msg: "Crawl Radio Okapi terminé — 12 nouveaux articles" },
  { time: "14:31:44", level: "info",    msg: "Embedding batch #47 généré (384 vecteurs)" },
  { time: "14:28:12", level: "warning", msg: "actualite.cd — timeout après 3 tentatives" },
  { time: "14:25:03", level: "info",    msg: "Crawl ACP terminé — 7 nouveaux articles" },
  { time: "14:20:55", level: "info",    msg: "TopicGateService — mots-clés rafraîchis (15 min)" },
  { time: "14:18:30", level: "error",   msg: "congoindependant.com — SSL cert expiring soon" },
  { time: "14:15:10", level: "info",    msg: "Crawl RFI Afrique terminé — 5 nouveaux articles" },
];

const STATS = [
  { icon: <Database size={16}/>,   label: "Articles indexés", value: "2 241",  sub: "+19 aujourd'hui",  color: "#60a5fa" },
  { icon: <Zap size={16}/>,        label: "Vecteurs pgvector", value: "2 241",  sub: "dim. 384",         color: "#a78bfa" },
  { icon: <Activity size={16}/>,   label: "Requêtes / 24 h",   value: "1 084",  sub: "↑ 12% vs hier",   color: "#34d399" },
  { icon: <Clock size={16}/>,      label: "Latence moyenne",   value: "6.4 s",  sub: "verdict Mistral",  color: "#fb923c" },
];

function StatusDot({ status }: { status: any }) 
{  const map = { ok: "#10b981", warning: "#f59e0b", error: "#ef4444" };
  return <span style={{ width: 7, height: 7, borderRadius: "50%", background: map[status] ?? "#475569", display: "inline-block", animation: status === "ok" ? "pulse 2.5s infinite" : "none" }}/>;
}

function LogLevel({ level }) {
  const map = {
    info:    { bg: "rgba(96,165,250,0.1)",  color: "#60a5fa",  label: "INFO" },
    warning: { bg: "rgba(245,158,11,0.1)",  color: "#fcd34d",  label: "WARN" },
    error:   { bg: "rgba(239,68,68,0.1)",   color: "#fca5a5",  label: "ERR" },
  };
  const s = map[level] ?? map.info;
  return (
    <span style={{
      background: s.bg, color: s.color, borderRadius: 5,
      padding: "1px 7px", fontSize: 10, fontWeight: 700, letterSpacing: "0.08em",
      minWidth: 36, textAlign: "center", display: "inline-block",
    }}>{s.label}</span>
  );
}

export default function AdminPage() {
  const [crawling, setCrawling]   = useState(false);
  const [syncing, setSyncing]     = useState(false);
  const [activeTab, setActiveTab] = useState("sources"); // sources | logs | system

  const startCrawl = () => {
    setCrawling(true);
    setTimeout(() => setCrawling(false), 3000);
  };
  const startSync = () => {
    setSyncing(true);
    setTimeout(() => setSyncing(false), 2500);
  };

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600&family=DM+Serif+Display:ital@1&display=swap');
        * { box-sizing: border-box; margin: 0; padding: 0; }
        @keyframes pulse  { 0%,100%{opacity:1} 50%{opacity:0.35} }
        @keyframes spin   { to{transform:rotate(360deg)} }
        @keyframes fadeUp { from{opacity:0;transform:translateY(8px)} to{opacity:1;transform:translateY(0)} }
        .row-in  { animation: fadeUp 0.2s ease forwards; }
        .act-btn:not(:disabled):hover  { opacity: 0.85 !important; transform: translateY(-1px); }
        .ghost-btn:hover               { background: rgba(255,255,255,0.09) !important; }
        .tab-btn:hover                 { color: #cbd5e1 !important; }
        .src-row:hover                 { background: rgba(255,255,255,0.05) !important; }
        .scroll::-webkit-scrollbar     { width: 4px; }
        .scroll::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.08); border-radius: 2px; }
      `}</style>

      <div style={{
        minHeight: "100vh", fontFamily: "'DM Sans', sans-serif", color: "#e2e8f0",
        background: "radial-gradient(ellipse 80% 50% at 80% -5%, rgba(29,78,216,0.22) 0%, transparent 55%), linear-gradient(180deg,#060c1a 0%,#080f20 60%,#050b18 100%)",
      }}>
        {/* Grid texture */}
        <div style={{
          position: "fixed", inset: 0, pointerEvents: "none", opacity: 0.03,
          backgroundImage: "linear-gradient(rgba(148,163,184,1) 1px,transparent 1px),linear-gradient(90deg,rgba(148,163,184,1) 1px,transparent 1px)",
          backgroundSize: "48px 48px",
        }}/>

        <div style={{ maxWidth: 1280, margin: "0 auto", padding: "18px 22px", position: "relative" }}>

          {/* NAV */}
          <header style={{
            display: "flex", alignItems: "center", justifyContent: "space-between",
            background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)",
            borderRadius: 16, padding: "10px 18px", backdropFilter: "blur(16px)",
            marginBottom: 18,
          }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <div style={{
                width: 30, height: 30, borderRadius: 9,
                background: "rgba(96,165,250,0.15)", border: "1px solid rgba(96,165,250,0.3)",
                display: "flex", alignItems: "center", justifyContent: "center",
              }}>
                <Shield size={14} color="#60a5fa"/>
              </div>
              <div>
                <span style={{ fontSize: 10, fontWeight: 600, letterSpacing: "0.3em", textTransform: "uppercase", color: "#60a5fa" }}>
                  RDC News Intelligence
                </span>
                <span style={{ fontSize: 10, color: "#334155", marginLeft: 10 }}>/ Console admin</span>
              </div>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                <span style={{ width: 6, height: 6, borderRadius: "50%", background: "#10b981", animation: "pulse 2s infinite" }}/>
                <span style={{ fontSize: 11, color: "#475569" }}>Tous systèmes opérationnels</span>
              </div>
              <button style={{
                display: "flex", alignItems: "center", gap: 6,
                background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.1)",
                color: "#94a3b8", borderRadius: 10, padding: "5px 12px", fontSize: 11, cursor: "pointer",
              }}>
                <ArrowLeft size={11}/> Accueil
              </button>
            </div>
          </header>

          {/* HERO ROW */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1.6fr", gap: 14, marginBottom: 14 }}>

            {/* Control card */}
            <div style={{
              background: "linear-gradient(145deg, #0f172a 0%, #1e3a6e 60%, #1d4ed8 100%)",
              border: "1px solid rgba(96,165,250,0.2)", borderRadius: 22,
              padding: "26px 24px",
              boxShadow: "0 20px 60px rgba(15,23,42,0.5)",
            }}>
              <p style={{ fontSize: 10, fontWeight: 600, letterSpacing: "0.28em", textTransform: "uppercase", color: "rgba(186,210,255,0.7)", marginBottom: 8 }}>
                Contrôle rapide
              </p>
              <h2 style={{
                fontFamily: "'DM Serif Display', serif", fontStyle: "italic",
                fontSize: 28, fontWeight: 400, color: "#fff", lineHeight: 1.1, marginBottom: 10,
              }}>Orchestrer, crawler, superviser.</h2>
              <p style={{ fontSize: 13, color: "rgba(186,210,255,0.65)", lineHeight: 1.65, marginBottom: 22 }}>
                Déclenche la collecte, synchronise l'index vectoriel et consulte les logs du pipeline en temps réel.
              </p>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
                {[
                  { label: "Lancer le crawl",      icon: crawling ? <RefreshCw size={13} style={{ animation: "spin 1s linear infinite" }}/> : <Play size={13}/>,    primary: true,  action: startCrawl,  disabled: crawling, text: crawling ? "Crawl en cours…" : "Lancer le crawl" },
                  { label: "Synchroniser l'index", icon: syncing  ? <RefreshCw size={13} style={{ animation: "spin 1s linear infinite" }}/> : <RotateCcw size={13}/>,primary: false, action: startSync,   disabled: syncing,  text: syncing  ? "Synchro…"        : "Synchroniser" },
                  { label: "Vérifier les sources", icon: <CheckCircle2 size={13}/>, primary: false, action: () => setActiveTab("sources"), text: "Vérifier sources" },
                  { label: "Consulter les logs",   icon: <List size={13}/>,         primary: false, action: () => setActiveTab("logs"),    text: "Voir les logs" },
                ].map(({ icon, primary, action, disabled, text }) => (
                  <button
                    key={text}
                    className="act-btn"
                    onClick={action}
                    disabled={disabled}
                    style={{
                      display: "flex", alignItems: "center", justifyContent: "center", gap: 7,
                      borderRadius: 14, padding: "11px 12px", fontSize: 12.5, fontWeight: 600,
                      cursor: disabled ? "default" : "pointer", transition: "all 0.2s",
                      background: primary ? "#fff" : "rgba(255,255,255,0.1)",
                      color: primary ? "#0f172a" : "#fff",
                      border: primary ? "none" : "1px solid rgba(255,255,255,0.15)",
                      opacity: disabled ? 0.6 : 1,
                    }}
                  >
                    {icon} {text}
                  </button>
                ))}
              </div>
            </div>

            {/* Stats grid */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
              {STATS.map(({ icon, label, value, sub, color }) => (
                <div key={label} style={{
                  background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)",
                  borderRadius: 18, padding: "20px", backdropFilter: "blur(12px)",
                }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
                    <div style={{
                      width: 32, height: 32, borderRadius: 10,
                      background: `${color}18`, border: `1px solid ${color}30`,
                      display: "flex", alignItems: "center", justifyContent: "center", color,
                    }}>{icon}</div>
                    <span style={{ fontSize: 11, color: "#475569", fontWeight: 500 }}>{label}</span>
                  </div>
                  <p style={{ fontSize: 28, fontWeight: 600, color: "#f1f5f9", letterSpacing: "-0.02em" }}>{value}</p>
                  <p style={{ fontSize: 11, color: "#334155", marginTop: 4 }}>{sub}</p>
                </div>
              ))}
            </div>
          </div>

          {/* TABS PANEL */}
          <div style={{
            background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)",
            borderRadius: 22, backdropFilter: "blur(16px)", overflow: "hidden",
          }}>
            {/* Tab bar */}
            <div style={{
              display: "flex", alignItems: "center", gap: 2,
              borderBottom: "1px solid rgba(255,255,255,0.07)", padding: "0 20px",
            }}>
              {[
                { id: "sources", icon: <Globe size={13}/>,    label: "Sources actives" },
                { id: "logs",    icon: <FileText size={13}/>,  label: "Logs système" },
                { id: "system",  icon: <Server size={13}/>,   label: "Infrastructure" },
              ].map(({ id, icon, label }) => (
                <button
                  key={id}
                  className="tab-btn"
                  onClick={() => setActiveTab(id)}
                  style={{
                    display: "flex", alignItems: "center", gap: 7,
                    padding: "14px 16px", fontSize: 12.5, fontWeight: 500,
                    background: "transparent", border: "none", cursor: "pointer",
                    color: activeTab === id ? "#f1f5f9" : "#475569",
                    borderBottom: activeTab === id ? "2px solid #3b82f6" : "2px solid transparent",
                    marginBottom: -1, transition: "color 0.2s",
                  }}
                >
                  {icon} {label}
                </button>
              ))}
            </div>

            {/* Tab content */}
            <div style={{ padding: "20px" }}>

              {/* SOURCES TAB */}
              {activeTab === "sources" && (
                <div>
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 14 }}>
                    <p style={{ fontSize: 12, color: "#475569" }}>{SOURCES.filter(s => s.status === "ok").length}/{SOURCES.length} sources opérationnelles</p>
                    <button className="ghost-btn" style={{
                      display: "flex", alignItems: "center", gap: 6,
                      background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.1)",
                      color: "#64748b", borderRadius: 10, padding: "5px 12px", fontSize: 11, cursor: "pointer",
                      transition: "background 0.2s",
                    }}>
                      <Search size={11}/> Rechercher une source
                    </button>
                  </div>

                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                    {SOURCES.map((src, i) => (
                      <div key={src.url} className="src-row row-in" style={{
                        display: "flex", alignItems: "center", gap: 12,
                        background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.07)",
                        borderRadius: 14, padding: "14px 16px", transition: "background 0.2s",
                        animationDelay: `${i * 0.04}s`,
                      }}>
                        <StatusDot status={src.status}/>
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <p style={{ fontSize: 13, fontWeight: 600, color: "#e2e8f0", marginBottom: 2 }}>{src.name}</p>
                          <p style={{ fontSize: 11, color: "#334155", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{src.url}</p>
                        </div>
                        <div style={{ textAlign: "right", flexShrink: 0 }}>
                          <p style={{ fontSize: 13, fontWeight: 600, color: "#60a5fa" }}>{src.articles.toLocaleString()}</p>
                          <p style={{ fontSize: 10, color: "#334155" }}>{src.lastCrawl}</p>
                        </div>
                        {src.status === "warning" && (
                          <AlertTriangle size={14} color="#f59e0b" style={{ flexShrink: 0 }}/>
                        )}
                        <ChevronRight size={13} color="#1e293b" style={{ flexShrink: 0 }}/>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* LOGS TAB */}
              {activeTab === "logs" && (
                <div>
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 14 }}>
                    <p style={{ fontSize: 12, color: "#475569" }}>7 entrées récentes</p>
                    <button className="ghost-btn" style={{
                      display: "flex", alignItems: "center", gap: 6,
                      background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.1)",
                      color: "#64748b", borderRadius: 10, padding: "5px 12px", fontSize: 11, cursor: "pointer",
                      transition: "background 0.2s",
                    }}>
                      <RefreshCw size={11}/> Actualiser
                    </button>
                  </div>

                  <div className="scroll" style={{
                    background: "rgba(0,0,0,0.3)", border: "1px solid rgba(255,255,255,0.06)",
                    borderRadius: 14, overflow: "hidden",
                    fontFamily: "'DM Mono', 'Fira Code', monospace",
                  }}>
                    {LOGS.map((log, i) => (
                      <div key={i} className="row-in" style={{
                        display: "flex", alignItems: "center", gap: 14,
                        padding: "10px 16px",
                        borderBottom: i < LOGS.length - 1 ? "1px solid rgba(255,255,255,0.04)" : "none",
                        animationDelay: `${i * 0.05}s`,
                      }}>
                        <span style={{ fontSize: 11, color: "#334155", minWidth: 62, flexShrink: 0 }}>{log.time}</span>
                        <LogLevel level={log.level}/>
                        <span style={{ fontSize: 12, color: log.level === "error" ? "#fca5a5" : log.level === "warning" ? "#fcd34d" : "#94a3b8" }}>
                          {log.msg}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* SYSTEM TAB */}
              {activeTab === "system" && (
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12 }}>
                  {[
                    { icon: <Cpu size={16}/>,        color: "#a78bfa", label: "Mistral-7B (Ollama)", lines: [["Statut", "En ligne"], ["Mémoire", "6.2 GB VRAM"], ["Modèle", "mistral:7b-q4"]] },
                    { icon: <HardDrive size={16}/>,   color: "#34d399", label: "PostgreSQL + pgvector", lines: [["Statut", "En ligne"], ["Taille DB", "1.4 GB"], ["Extension", "pgvector 0.7"]] },
                    { icon: <Wifi size={16}/>,        color: "#fb923c", label: "FastAPI Backend", lines: [["Statut", "En ligne"], ["Workers", "4 async"], ["Version", "0.115.x"]] },
                    { icon: <TrendingUp size={16}/>,  color: "#60a5fa", label: "Scheduler (CRON)", lines: [["Crawl", "15 min"], ["Re-embed", "1 h"], ["Proch. crawl", "dans 3 min"]] },
                    { icon: <Globe size={16}/>,       color: "#f472b6", label: "WhatsApp Cloud API", lines: [["Statut", "Connecté"], ["Webhook", "Actif"], ["Canal", "Business"]] },
                    { icon: <Server size={16}/>,      color: "#fbbf24", label: "Telegram Bot API", lines: [["Statut", "Connecté"], ["Mode", "Webhook"], ["Groupes", "12 actifs"]] },
                  ].map(({ icon, color, label, lines }) => (
                    <div key={label} style={{
                      background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)",
                      borderRadius: 16, padding: "18px",
                    }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 14 }}>
                        <div style={{
                          width: 30, height: 30, borderRadius: 9,
                          background: `${color}18`, border: `1px solid ${color}28`,
                          display: "flex", alignItems: "center", justifyContent: "center", color,
                        }}>{icon}</div>
                        <span style={{ fontSize: 12, fontWeight: 600, color: "#cbd5e1" }}>{label}</span>
                      </div>
                      <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                        {lines.map(([k, v]) => (
                          <div key={k} style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                            <span style={{ fontSize: 11, color: "#334155" }}>{k}</span>
                            <span style={{ fontSize: 11, fontWeight: 600, color: v === "En ligne" || v === "Connecté" || v === "Actif" ? "#34d399" : "#94a3b8" }}>{v}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

        </div>
      </div>
    </>
  );
}