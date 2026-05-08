"use client";

import { useState, useEffect, useRef } from "react";
import { Send, Shield, Zap, Database, CheckCircle, XCircle, AlertCircle, HelpCircle, Bot, User, ArrowRight } from "lucide-react";

const DEMO_MESSAGES = [
  { role: "user", text: "Est-ce vrai que Kinshasa a été bouclée ce matin ?" },
  {
    role: "bot", verdict: "FAUX",
    text: "Selon Radio Okapi (6 mai 2026), aucune restriction de circulation n'a été signalée à Kinshasa ce matin. Les sources officielles démentent cette information.",
    sources: ["Radio Okapi", "ACP"],
  },
  { role: "user", text: "Qu'en est-il de la situation à Goma ?" },
  {
    role: "bot", verdict: "VRAI",
    text: "D'après ACP (5 mai 2026), des tensions ont été rapportées dans la commune de Goma-nord. La situation est sous surveillance des forces de l'ordre.",
    sources: ["ACP", "actualite.cd"],
  },
];

const TYPING_SPEED = 16;

function useTypewriter(text, active) {
  const [displayed, setDisplayed] = useState("");
  useEffect(() => {
    if (!active) { setDisplayed(text); return; }
    setDisplayed("");
    let i = 0;
    const id = setInterval(() => {
      i++;
      setDisplayed(text.slice(0, i));
      if (i >= text.length) clearInterval(id);
    }, TYPING_SPEED);
    return () => clearInterval(id);
  }, [text, active]);
  return displayed;
}

function VerdictBadge({ verdict }) {
  const map = {
    VRAI:            { bg: "rgba(16,185,129,0.15)", color: "#6ee7b7", ring: "rgba(16,185,129,0.3)", icon: <CheckCircle size={11}/> },
    FAUX:            { bg: "rgba(239,68,68,0.15)",  color: "#fca5a5", ring: "rgba(239,68,68,0.3)",  icon: <XCircle size={11}/> },
    "IMPRÉCIS":      { bg: "rgba(245,158,11,0.15)", color: "#fcd34d", ring: "rgba(245,158,11,0.3)", icon: <AlertCircle size={11}/> },
    "NON VÉRIFIABLE":{ bg: "rgba(100,116,139,0.15)",color: "#94a3b8", ring: "rgba(100,116,139,0.3)",icon: <HelpCircle size={11}/> },
  };
  const s = map[verdict] ?? map["NON VÉRIFIABLE"];
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", gap: 4,
      background: s.bg, color: s.color,
      border: `1px solid ${s.ring}`,
      borderRadius: 999, padding: "2px 10px",
      fontSize: 10, fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase",
    }}>
      {s.icon} {verdict}
    </span>
  );
}

function BotMessage({ msg, animate }) {
  const displayed = useTypewriter(msg.text, animate);
  return (
    <div style={{ display: "flex", gap: 10, alignItems: "flex-start" }}>
      <div style={{
        width: 28, height: 28, borderRadius: "50%", flexShrink: 0, marginTop: 2,
        background: "rgba(96,165,250,0.15)", border: "1px solid rgba(96,165,250,0.3)",
        display: "flex", alignItems: "center", justifyContent: "center", color: "#60a5fa",
      }}>
        <Bot size={13} />
      </div>
      <div style={{ flex: 1 }}>
        {msg.verdict && <div style={{ marginBottom: 6 }}><VerdictBadge verdict={msg.verdict} /></div>}
        <p style={{ margin: 0, fontSize: 13, lineHeight: 1.65, color: "#cbd5e1" }}>
          {displayed}
          {animate && displayed.length < msg.text.length && (
            <span style={{ animation: "blink 1s step-end infinite", marginLeft: 1 }}>▌</span>
          )}
        </p>
        {msg.sources && (
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 8 }}>
            {msg.sources.map(s => (
              <span key={s} style={{
                fontSize: 11, color: "#64748b", background: "rgba(255,255,255,0.05)",
                border: "1px solid rgba(255,255,255,0.1)", borderRadius: 6, padding: "2px 8px",
              }}>{s}</span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function UserMessage({ text }) {
  return (
    <div style={{ display: "flex", justifyContent: "flex-end" }}>
      <div style={{
        maxWidth: "78%", background: "#2563eb", color: "#fff",
        borderRadius: "18px 18px 4px 18px",
        padding: "10px 14px", fontSize: 13, lineHeight: 1.6,
        boxShadow: "0 4px 20px rgba(37,99,235,0.35)",
      }}>{text}</div>
    </div>
  );
}

function TypingIndicator() {
  return (
    <div style={{ display: "flex", gap: 10, alignItems: "flex-start" }}>
      <div style={{
        width: 28, height: 28, borderRadius: "50%", flexShrink: 0,
        background: "rgba(96,165,250,0.15)", border: "1px solid rgba(96,165,250,0.3)",
        display: "flex", alignItems: "center", justifyContent: "center", color: "#60a5fa",
      }}>
        <Bot size={13} />
      </div>
      <div style={{
        display: "flex", alignItems: "center", gap: 5,
        background: "rgba(255,255,255,0.06)", borderRadius: "18px 18px 18px 4px",
        padding: "12px 16px", border: "1px solid rgba(255,255,255,0.08)",
      }}>
        {[0, 0.18, 0.36].map(d => (
          <span key={d} style={{
            width: 6, height: 6, borderRadius: "50%", background: "#64748b",
            animation: `bounce 1s ease-in-out ${d}s infinite`,
            display: "inline-block",
          }} />
        ))}
      </div>
    </div>
  );
}

export default function App() {
  const [visibleCount, setVisibleCount] = useState(0);
  const [inputVal, setInputVal] = useState("");
  const bottomRef = useRef(null);

  useEffect(() => {
    if (visibleCount >= DEMO_MESSAGES.length) return;
    const prev = DEMO_MESSAGES[visibleCount - 1];
    const delay = visibleCount === 0 ? 900 : prev?.role === "user" ? 500 : 2400;
    const t = setTimeout(() => setVisibleCount(c => c + 1), delay);
    return () => clearTimeout(t);
  }, [visibleCount]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [visibleCount]);

  const showTyping = visibleCount < DEMO_MESSAGES.length && DEMO_MESSAGES[visibleCount]?.role === "bot";

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600&family=DM+Serif+Display:ital@1&display=swap');
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { background: #060c1a; }
        @keyframes blink { 0%,100%{opacity:1} 50%{opacity:0} }
        @keyframes bounce { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-5px)} }
        @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.4} }
        @keyframes fadeSlideUp { from{opacity:0;transform:translateY(12px)} to{opacity:1;transform:translateY(0)} }
        .stat-card:hover { background: rgba(255,255,255,0.07) !important; }
        .btn-primary:hover { background: #3b82f6 !important; transform: translateY(-1px); }
        .btn-secondary:hover { background: rgba(255,255,255,0.1) !important; transform: translateY(-1px); }
        .chat-scroll::-webkit-scrollbar { width: 4px; }
        .chat-scroll::-webkit-scrollbar-track { background: transparent; }
        .chat-scroll::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 2px; }
        .msg-enter { animation: fadeSlideUp 0.3s ease forwards; }
      `}</style>

      <div style={{
        minHeight: "100vh", fontFamily: "'DM Sans', sans-serif", color: "#e2e8f0",
        background: "radial-gradient(ellipse 90% 55% at 50% -5%, rgba(29,78,216,0.25) 0%, transparent 55%), linear-gradient(180deg, #060c1a 0%, #080f20 60%, #050b18 100%)",
        display: "flex", flexDirection: "column",
      }}>
        {/* Grid texture */}
        <div style={{
          position: "fixed", inset: 0, pointerEvents: "none", opacity: 0.03,
          backgroundImage: "linear-gradient(rgba(148,163,184,1) 1px, transparent 1px), linear-gradient(90deg, rgba(148,163,184,1) 1px, transparent 1px)",
          backgroundSize: "48px 48px",
        }} />

        <div style={{ maxWidth: 1200, width: "100%", margin: "0 auto", padding: "20px 24px", display: "flex", flexDirection: "column", flex: 1, position: "relative" }}>

          {/* NAV */}
          <header style={{
            display: "flex", alignItems: "center", justifyContent: "space-between",
            background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)",
            borderRadius: 18, padding: "12px 20px", backdropFilter: "blur(16px)",
          }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <div style={{
                width: 32, height: 32, borderRadius: 10,
                background: "rgba(96,165,250,0.15)", border: "1px solid rgba(96,165,250,0.3)",
                display: "flex", alignItems: "center", justifyContent: "center",
              }}>
                <Shield size={15} color="#60a5fa" />
              </div>
              <div>
                <p style={{ fontSize: 10, fontWeight: 600, letterSpacing: "0.3em", textTransform: "uppercase", color: "#60a5fa" }}>RDC News Intelligence</p>
              </div>
            </div>
            <div style={{ display: "flex", gap: 8 }}>
              <button style={{
                background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.1)",
                color: "#cbd5e1", borderRadius: 12, padding: "6px 16px", fontSize: 12, fontWeight: 500, cursor: "pointer",
              }}>Connexion</button>
              <button style={{
                background: "#2563eb", border: "none", color: "#fff",
                borderRadius: 12, padding: "6px 16px", fontSize: 12, fontWeight: 600, cursor: "pointer",
                boxShadow: "0 4px 20px rgba(37,99,235,0.4)",
              }}>Admin</button>
            </div>
          </header>

          {/* HERO */}
          <div style={{
            flex: 1, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 48,
            alignItems: "center", padding: "48px 0",
          }}>

            {/* LEFT */}
            <div style={{ maxWidth: 520 }}>
              <div style={{
                display: "inline-flex", alignItems: "center", gap: 8,
                background: "rgba(96,165,250,0.1)", border: "1px solid rgba(96,165,250,0.25)",
                borderRadius: 999, padding: "6px 14px", fontSize: 12, fontWeight: 500, color: "#93c5fd",
                marginBottom: 28,
              }}>
                <span style={{ width: 6, height: 6, borderRadius: "50%", background: "#60a5fa", animation: "pulse 2s infinite" }} />
                Fact-checking en temps réel · WhatsApp &amp; Telegram
              </div>

              <h2 style={{
                fontFamily: "'DM Serif Display', Georgia, serif",
                fontStyle: "italic", fontWeight: 400,
                fontSize: 46, lineHeight: 1.06, letterSpacing: "-0.01em",
                color: "#f1f5f9", marginBottom: 20,
              }}>
                La vérité, avant que la rumeur ne se propage.
              </h2>

              <p style={{ fontSize: 15, lineHeight: 1.75, color: "#64748b", marginBottom: 32 }}>
                Un bot intelligent qui vérifie automatiquement les informations dans vos groupes WhatsApp et Telegram — basé uniquement sur des sources vérifiées de la presse congolaise.
              </p>

              <div style={{ display: "flex", gap: 12, marginBottom: 40, flexWrap: "wrap" }}>
                <button className="btn-primary" style={{
                  display: "inline-flex", alignItems: "center", gap: 8,
                  background: "#2563eb", color: "#fff", border: "none",
                  borderRadius: 16, padding: "12px 24px", fontSize: 14, fontWeight: 600, cursor: "pointer",
                  boxShadow: "0 8px 30px rgba(37,99,235,0.4)", transition: "all 0.2s",
                }}>
                  Poser une question <ArrowRight size={15} />
                </button>
                <button className="btn-secondary" style={{
                  display: "inline-flex", alignItems: "center", gap: 8,
                  background: "rgba(255,255,255,0.05)", color: "#cbd5e1",
                  border: "1px solid rgba(255,255,255,0.12)",
                  borderRadius: 16, padding: "12px 24px", fontSize: 14, fontWeight: 600, cursor: "pointer",
                  transition: "all 0.2s",
                }}>
                  Tableau de bord
                </button>
              </div>

              {/* Stats */}
              <div style={{
                display: "grid", gridTemplateColumns: "1fr 1fr 1fr",
                background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)",
                borderRadius: 16, overflow: "hidden",
              }}>
                {[
                  { icon: <Database size={14}/>, label: "Sources", value: "12+", sub: "presse RDC vérifiée" },
                  { icon: <Zap size={14}/>,      label: "Délai",   value: "< 8s", sub: "verdict moyen" },
                  { icon: <Shield size={14}/>,   label: "Thèmes",  value: "4",    sub: "politique · santé · guerre · sport" },
                ].map((s, i) => (
                  <div key={s.label} className="stat-card" style={{
                    padding: "16px 18px", transition: "background 0.2s",
                    borderRight: i < 2 ? "1px solid rgba(255,255,255,0.06)" : "none",
                  }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 6, color: "#475569", marginBottom: 6 }}>
                      {s.icon}
                      <span style={{ fontSize: 10, textTransform: "uppercase", letterSpacing: "0.2em", fontWeight: 600 }}>{s.label}</span>
                    </div>
                    <p style={{ fontSize: 22, fontWeight: 600, color: "#f1f5f9", marginBottom: 3 }}>{s.value}</p>
                    <p style={{ fontSize: 11, color: "#475569", lineHeight: 1.4 }}>{s.sub}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* RIGHT — Chat demo */}
            <div style={{ position: "relative" }}>
              <div style={{
                position: "absolute", inset: -24, borderRadius: 40,
                background: "rgba(37,99,235,0.08)", filter: "blur(40px)", pointerEvents: "none",
              }} />
              <div style={{
                position: "relative", borderRadius: 24,
                background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.09)",
                backdropFilter: "blur(20px)", overflow: "hidden",
                boxShadow: "0 30px 80px rgba(0,0,0,0.4)",
              }}>
                {/* Chat header */}
                <div style={{
                  display: "flex", alignItems: "center", gap: 10,
                  borderBottom: "1px solid rgba(255,255,255,0.07)", padding: "14px 18px",
                }}>
                  <div style={{
                    width: 32, height: 32, borderRadius: "50%",
                    background: "rgba(96,165,250,0.15)", border: "1px solid rgba(96,165,250,0.3)",
                    display: "flex", alignItems: "center", justifyContent: "center", color: "#60a5fa",
                  }}>
                    <Bot size={15} />
                  </div>
                  <div style={{ flex: 1 }}>
                    <p style={{ fontSize: 13, fontWeight: 600, color: "#f1f5f9" }}>RDC News Bot</p>
                    <div style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 2 }}>
                      <span style={{ width: 6, height: 6, borderRadius: "50%", background: "#10b981", animation: "pulse 2s infinite" }} />
                      <span style={{ fontSize: 11, color: "#475569" }}>Actif · Corpus local vérifié</span>
                    </div>
                  </div>
                  <div style={{ display: "flex", gap: 5 }}>
                    {["#ef4444", "#f59e0b", "#10b981"].map(c => (
                      <span key={c} style={{ width: 10, height: 10, borderRadius: "50%", background: c, opacity: 0.7 }} />
                    ))}
                  </div>
                </div>

                {/* Messages */}
                <div className="chat-scroll" style={{ height: 280, overflowY: "auto", padding: "16px 18px", display: "flex", flexDirection: "column", gap: 16 }}>
                  {DEMO_MESSAGES.slice(0, visibleCount).map((msg, i) => (
                    <div key={i} className="msg-enter">
                      {msg.role === "user"
                        ? <UserMessage text={msg.text} />
                        : <BotMessage msg={msg} animate={i === visibleCount - 1} />
                      }
                    </div>
                  ))}
                  {showTyping && <TypingIndicator />}
                  <div ref={bottomRef} />
                </div>

                {/* Input */}
                <div style={{ borderTop: "1px solid rgba(255,255,255,0.07)", padding: "12px 14px" }}>
                  <div style={{
                    display: "flex", alignItems: "center", gap: 10,
                    background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.1)",
                    borderRadius: 14, padding: "9px 12px",
                  }}>
                    <User size={14} color="#475569" />
                    <input
                      value={inputVal}
                      onChange={e => setInputVal(e.target.value)}
                      placeholder="Vérifier une information…"
                      style={{
                        flex: 1, background: "transparent", border: "none", outline: "none",
                        fontSize: 13, color: "#e2e8f0",
                      }}
                    />
                    <button
                      disabled={!inputVal.trim()}
                      style={{
                        width: 28, height: 28, borderRadius: 8, border: "none", cursor: inputVal.trim() ? "pointer" : "default",
                        background: inputVal.trim() ? "#2563eb" : "rgba(255,255,255,0.08)",
                        display: "flex", alignItems: "center", justifyContent: "center",
                        transition: "background 0.2s",
                      }}
                    >
                      <Send size={12} color={inputVal.trim() ? "#fff" : "#475569"} />
                    </button>
                  </div>
                  <p style={{ textAlign: "center", fontSize: 10, color: "#334155", marginTop: 8 }}>
                    Sources : Radio Okapi · ACP · actualite.cd · et 9 autres
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* FOOTER */}
          <footer style={{
            display: "flex", justifyContent: "space-between", alignItems: "center",
            borderTop: "1px solid rgba(255,255,255,0.05)", paddingTop: 20,
            fontSize: 11, color: "#334155",
          }}>
            <p>© 2026 RDC News Intelligence</p>
            <div style={{ display: "flex", gap: 24 }}>
              {["Espace client", "Administration", "Documentation"].map(l => (
                <span key={l} style={{ cursor: "pointer", transition: "color 0.2s" }}
                  onMouseEnter={e => e.target.style.color = "#64748b"}
                  onMouseLeave={e => e.target.style.color = "#334155"}
                >{l}</span>
              ))}
            </div>
          </footer>
        </div>
      </div>
    </>
  );
}