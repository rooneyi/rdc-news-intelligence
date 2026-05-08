"use client";

import { useState, useRef, useEffect } from "react";
import {
  Send, Shield, Clock, ChevronRight, Plus, Search,
  BookOpen, Star, Settings, Bot, User, Loader2,
  AlertCircle, Newspaper, Activity, Swords, Trophy, Home
} from "lucide-react";

const HISTORY = [
  { icon: <Swords size={12}/>,   text: "Constant Mutamba est mort ?" },
  { icon: <Activity size={12}/>, text: "Actualités santé RDC aujourd'hui" },
  { icon: <Swords size={12}/>,   text: "Résumé guerre à l'Est" },
  { icon: <Trophy size={12}/>,   text: "Points sport de la semaine" },
  { icon: <Newspaper size={12}/>,text: "Vérifier une image reçue" },
];

const SHORTCUTS = [
  { icon: <Plus size={14}/>,     label: "Nouveau chat" },
  { icon: <Search size={14}/>,   label: "Rechercher" },
  { icon: <BookOpen size={14}/>, label: "Bibliothèque" },
  { icon: <Star size={14}/>,     label: "Favoris" },
  { icon: <Settings size={14}/>, label: "Paramètres" },
];

const WELCOME = {
  id: 1, role: "assistant",
  content: "Bienvenue sur ton espace client. Pose une question sur la politique, le sport, la santé ou la guerre en RDC — je réponds avec des sources vérifiées.",
  meta: "Canal web",
};

function VerdictBadge({ text }) {
  if (!text) return null;
  const upper = text.toUpperCase();
  const styles = {
    VRAI:  { bg: "rgba(16,185,129,0.15)", color: "#6ee7b7", border: "rgba(16,185,129,0.3)" },
    FAUX:  { bg: "rgba(239,68,68,0.15)",  color: "#fca5a5", border: "rgba(239,68,68,0.3)" },
    "IMPRÉCIS": { bg: "rgba(245,158,11,0.15)", color: "#fcd34d", border: "rgba(245,158,11,0.3)" },
  };
  const found = Object.keys(styles).find(k => upper.includes(k));
  if (!found) return null;
  const s = styles[found];
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", gap: 4,
      background: s.bg, color: s.color, border: `1px solid ${s.border}`,
      borderRadius: 999, padding: "2px 10px",
      fontSize: 10, fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase",
      marginBottom: 6,
    }}>{found}</span>
  );
}

function AssistantBubble({ msg }) {
  const lines = msg.content.split("\n").filter(Boolean);
  const verdictLine = lines.find(l => /VRAI|FAUX|IMPRÉCIS/i.test(l));
  const sourceLine  = lines.find(l => /source|lien|http/i.test(l));
  const bodyLines   = lines.filter(l => l !== verdictLine && l !== sourceLine);

  return (
    <div style={{ display: "flex", gap: 10, alignItems: "flex-start", maxWidth: "88%" }}>
      <div style={{
        width: 30, height: 30, borderRadius: "50%", flexShrink: 0, marginTop: 2,
        background: "rgba(96,165,250,0.12)", border: "1px solid rgba(96,165,250,0.25)",
        display: "flex", alignItems: "center", justifyContent: "center", color: "#60a5fa",
      }}>
        <Bot size={14}/>
      </div>
      <div style={{
        background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.09)",
        borderRadius: "18px 18px 18px 4px", padding: "14px 16px",
        backdropFilter: "blur(8px)",
      }}>
        {verdictLine && <VerdictBadge text={verdictLine}/>}
        <p style={{ margin: 0, fontSize: 13.5, lineHeight: 1.7, color: "#cbd5e1", whiteSpace: "pre-wrap" }}>
          {bodyLines.join("\n") || msg.content}
        </p>
        {sourceLine && (
          <p style={{ margin: "8px 0 0", fontSize: 11, color: "#475569" }}>{sourceLine}</p>
        )}
        {msg.meta && (
          <p style={{ margin: "8px 0 0", fontSize: 11, color: "#334155" }}>{msg.meta}</p>
        )}
      </div>
    </div>
  );
}

function UserBubble({ msg }) {
  return (
    <div style={{ display: "flex", justifyContent: "flex-end", gap: 10, alignItems: "flex-start" }}>
      <div style={{
        maxWidth: "80%", background: "#2563eb", color: "#fff",
        borderRadius: "18px 18px 4px 18px",
        padding: "12px 16px", fontSize: 13.5, lineHeight: 1.65,
        boxShadow: "0 6px 24px rgba(37,99,235,0.35)",
      }}>{msg.content}</div>
      <div style={{
        width: 30, height: 30, borderRadius: "50%", flexShrink: 0, marginTop: 2,
        background: "rgba(255,255,255,0.08)", border: "1px solid rgba(255,255,255,0.12)",
        display: "flex", alignItems: "center", justifyContent: "center", color: "#94a3b8",
      }}>
        <User size={14}/>
      </div>
    </div>
  );
}

function TypingBubble() {
  return (
    <div style={{ display: "flex", gap: 10, alignItems: "flex-start" }}>
      <div style={{
        width: 30, height: 30, borderRadius: "50%", flexShrink: 0,
        background: "rgba(96,165,250,0.12)", border: "1px solid rgba(96,165,250,0.25)",
        display: "flex", alignItems: "center", justifyContent: "center", color: "#60a5fa",
      }}>
        <Bot size={14}/>
      </div>
      <div style={{
        display: "flex", alignItems: "center", gap: 5,
        background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.09)",
        borderRadius: "18px 18px 18px 4px", padding: "14px 18px",
      }}>
        {[0, 0.18, 0.36].map(d => (
          <span key={d} style={{
            width: 6, height: 6, borderRadius: "50%", background: "#475569",
            display: "inline-block", animation: `bounce 1s ease-in-out ${d}s infinite`,
          }}/>
        ))}
      </div>
    </div>
  );
}

export default function ClientPage() {
  const [query, setQuery]     = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState(null);
  const [messages, setMessages] = useState([WELCOME]);
  const [sideOpen, setSideOpen] = useState(true);
  const bottomRef = useRef(null);
  const textareaRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const handleKey = (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSubmit(); }
  };

  const handleSubmit = async () => {
    const trimmed = query.trim();
    if (!trimmed || loading) return;
    setError(null);
    setLoading(true);

    const userMsg = { id: Date.now(), role: "user", content: trimmed, meta: "Toi" };
    const asstId  = Date.now() + 1;
    setMessages(prev => [...prev, userMsg, { id: asstId, role: "assistant", content: "", meta: "Génération…" }]);
    setQuery("");

    try {
      const res = await fetch("/api/fastapi/rag/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: trimmed }),
      });

      if (!res.ok) {
        const p = await res.json().catch(() => ({}));
        throw new Error(p?.error ?? "Erreur serveur.");
      }

      const reader  = res.body.getReader();
      const decoder = new TextDecoder();
      let buf = "", summary = "", srcCount = 0;

      const update = (content, meta) =>
        setMessages(prev => prev.map(m => m.id === asstId ? { ...m, content, meta } : m));

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        const lines = buf.split("\n"); buf = lines.pop() ?? "";
        for (const line of lines) {
          if (!line.trim()) continue;
          let ev; try { ev = JSON.parse(line); } catch { continue; }
          if (ev.type === "sources") { srcCount = Array.isArray(ev.sources) ? ev.sources.length : 0; update(summary || "Analyse…", `${srcCount} source(s)`); }
          else if (ev.type === "summary_chunk") { summary += ev.text ?? ""; update(summary, `${srcCount} source(s)`); }
          else if (ev.type === "error") { setError(ev.message ?? "Erreur IA."); update(summary || "Erreur.", "Erreur"); break; }
          else if (ev.type === "done") update(summary || "Aucune réponse générée.", `${srcCount} source(s)`);
        }
      }
    } catch (err) {
      setError(err.message ?? "Impossible de joindre le service IA.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600&family=DM+Serif+Display:ital@1&display=swap');
        * { box-sizing: border-box; margin: 0; padding: 0; }
        @keyframes bounce { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-5px)} }
        @keyframes pulse  { 0%,100%{opacity:1} 50%{opacity:0.4} }
        @keyframes fadeUp { from{opacity:0;transform:translateY(8px)} to{opacity:1;transform:translateY(0)} }
        .msg-in { animation: fadeUp 0.25s ease forwards; }
        .side-btn:hover { background: rgba(255,255,255,0.07) !important; }
        .hist-btn:hover { background: rgba(255,255,255,0.06) !important; border-color: rgba(96,165,250,0.3) !important; }
        .send-btn:not(:disabled):hover { background: #3b82f6 !important; }
        .chat-scroll::-webkit-scrollbar { width: 4px; }
        .chat-scroll::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.08); border-radius: 2px; }
        textarea::placeholder { color: #334155; }
        textarea { color: #e2e8f0; }
      `}</style>

      <div style={{
        minHeight: "100vh", fontFamily: "'DM Sans', sans-serif",
        background: "radial-gradient(ellipse 80% 50% at 20% -5%, rgba(29,78,216,0.2) 0%, transparent 50%), linear-gradient(180deg,#060c1a 0%,#080f20 60%,#050b18 100%)",
        display: "flex", flexDirection: "column",
      }}>
        {/* Grid texture */}
        <div style={{
          position: "fixed", inset: 0, pointerEvents: "none", opacity: 0.03,
          backgroundImage: "linear-gradient(rgba(148,163,184,1) 1px,transparent 1px),linear-gradient(90deg,rgba(148,163,184,1) 1px,transparent 1px)",
          backgroundSize: "48px 48px",
        }}/>

        <div style={{ maxWidth: 1320, width: "100%", margin: "0 auto", padding: "16px 20px", display: "flex", flexDirection: "column", flex: 1, gap: 12, position: "relative" }}>

          {/* TOP NAV */}
          <header style={{
            display: "flex", alignItems: "center", justifyContent: "space-between",
            background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)",
            borderRadius: 16, padding: "10px 18px", backdropFilter: "blur(16px)",
          }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <div style={{
                width: 30, height: 30, borderRadius: 9,
                background: "rgba(96,165,250,0.15)", border: "1px solid rgba(96,165,250,0.3)",
                display: "flex", alignItems: "center", justifyContent: "center",
              }}>
                <Shield size={14} color="#60a5fa"/>
              </div>
              <span style={{ fontSize: 10, fontWeight: 600, letterSpacing: "0.3em", textTransform: "uppercase", color: "#60a5fa" }}>
                RDC News Intelligence
              </span>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                <span style={{ width: 6, height: 6, borderRadius: "50%", background: "#10b981", animation: "pulse 2s infinite" }}/>
                <span style={{ fontSize: 11, color: "#475569" }}>Moteur actif</span>
              </div>
              <button
                onClick={() => setSideOpen(o => !o)}
                style={{ background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.1)", color: "#94a3b8", borderRadius: 10, padding: "5px 12px", fontSize: 11, cursor: "pointer" }}
              >
                {sideOpen ? "Masquer sidebar" : "Sidebar"}
              </button>
              <button style={{
                background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.1)",
                color: "#94a3b8", borderRadius: 10, padding: "5px 12px", fontSize: 11,
                display: "flex", alignItems: "center", gap: 5, cursor: "pointer",
              }}>
                <Home size={12}/> Accueil
              </button>
            </div>
          </header>

          {/* MAIN LAYOUT */}
          <div style={{ flex: 1, display: "grid", gridTemplateColumns: sideOpen ? "240px 1fr" : "1fr", gap: 12 }}>

            {/* SIDEBAR */}
            {sideOpen && (
              <aside style={{
                background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)",
                borderRadius: 20, padding: 14, backdropFilter: "blur(16px)",
                display: "flex", flexDirection: "column", gap: 20,
              }}>
                {/* Profile pill */}
                <div style={{
                  display: "flex", alignItems: "center", gap: 10,
                  background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.09)",
                  borderRadius: 14, padding: "10px 12px",
                }}>
                  <div style={{
                    width: 34, height: 34, borderRadius: "50%",
                    background: "linear-gradient(135deg,#2563eb,#60a5fa)",
                    display: "flex", alignItems: "center", justifyContent: "center",
                    fontSize: 13, fontWeight: 700, color: "#fff",
                  }}>A</div>
                  <div>
                    <p style={{ fontSize: 13, fontWeight: 600, color: "#e2e8f0" }}>RDC Assistant</p>
                    <p style={{ fontSize: 10, color: "#475569" }}>Espace client</p>
                  </div>
                </div>

                {/* Shortcuts */}
                <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                  {SHORTCUTS.map(({ icon, label }) => (
                    <button key={label} className="side-btn" style={{
                      display: "flex", alignItems: "center", gap: 10,
                      background: "transparent", border: "none", color: "#64748b",
                      borderRadius: 12, padding: "9px 12px", fontSize: 13, cursor: "pointer",
                      transition: "background 0.2s", textAlign: "left", width: "100%",
                    }}>
                      <span style={{ color: "#475569" }}>{icon}</span> {label}
                    </button>
                  ))}
                </div>

                {/* Divider */}
                <div style={{ height: 1, background: "rgba(255,255,255,0.06)" }}/>

                {/* History */}
                <div>
                  <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 10 }}>
                    <Clock size={11} color="#334155"/>
                    <p style={{ fontSize: 10, fontWeight: 600, letterSpacing: "0.2em", textTransform: "uppercase", color: "#334155" }}>Récents</p>
                  </div>
                  <div style={{ display: "flex", flexDirection: "column", gap: 5 }}>
                    {HISTORY.map(({ icon, text }) => (
                      <button key={text} className="hist-btn" style={{
                        display: "flex", alignItems: "center", gap: 8,
                        background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.07)",
                        borderRadius: 10, padding: "8px 10px",
                        fontSize: 12, color: "#64748b", cursor: "pointer",
                        transition: "all 0.2s", textAlign: "left", width: "100%",
                      }}>
                        <span style={{ color: "#334155", flexShrink: 0 }}>{icon}</span>
                        <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{text}</span>
                        <ChevronRight size={10} style={{ marginLeft: "auto", flexShrink: 0, color: "#1e293b" }}/>
                      </button>
                    ))}
                  </div>
                </div>

                {/* Canal badge */}
                <div style={{ marginTop: "auto" }}>
                  <div style={{
                    background: "rgba(37,99,235,0.1)", border: "1px solid rgba(37,99,235,0.2)",
                    borderRadius: 12, padding: "10px 12px",
                  }}>
                    <p style={{ fontSize: 10, fontWeight: 600, letterSpacing: "0.2em", textTransform: "uppercase", color: "#3b82f6", marginBottom: 4 }}>Canal actif</p>
                    <p style={{ fontSize: 12, color: "#60a5fa" }}>Web · Corpus RDC vérifié</p>
                  </div>
                </div>
              </aside>
            )}

            {/* CHAT PANEL */}
            <div style={{
              background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)",
              borderRadius: 20, backdropFilter: "blur(16px)",
              display: "flex", flexDirection: "column", overflow: "hidden",
            }}>
              {/* Chat header */}
              <div style={{
                display: "flex", alignItems: "center", justifyContent: "space-between",
                borderBottom: "1px solid rgba(255,255,255,0.07)", padding: "14px 20px",
              }}>
                <div>
                  <p style={{ fontSize: 10, fontWeight: 600, letterSpacing: "0.28em", textTransform: "uppercase", color: "#3b82f6" }}>
                    Assistant Client
                  </p>
                  <h1 style={{
                    fontSize: 16, fontWeight: 600, color: "#f1f5f9", marginTop: 2,
                    fontFamily: "'DM Serif Display', serif", fontStyle: "italic",
                  }}>Conversation Web</h1>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <span style={{
                    background: "rgba(16,185,129,0.12)", color: "#6ee7b7",
                    border: "1px solid rgba(16,185,129,0.25)",
                    borderRadius: 999, padding: "3px 12px", fontSize: 11, fontWeight: 600,
                  }}>Opérationnel</span>
                </div>
              </div>

              {/* Messages */}
              <div className="chat-scroll" style={{
                flex: 1, overflowY: "auto", padding: "20px",
                display: "flex", flexDirection: "column", gap: 18,
                minHeight: 0,
              }}>
                {messages.map((msg, i) => (
                  <div key={msg.id} className="msg-in" style={{ animationDelay: `${i * 0.02}s` }}>
                    {msg.role === "user"
                      ? <UserBubble msg={msg}/>
                      : <AssistantBubble msg={msg}/>
                    }
                  </div>
                ))}
                {loading && (
                  <div className="msg-in"><TypingBubble/></div>
                )}
                <div ref={bottomRef}/>
              </div>

              {/* Error */}
              {error && (
                <div style={{
                  display: "flex", alignItems: "center", gap: 8,
                  background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.2)",
                  borderRadius: 12, margin: "0 20px", padding: "10px 14px",
                  fontSize: 12, color: "#fca5a5",
                }}>
                  <AlertCircle size={14}/> {error}
                </div>
              )}

              {/* Input */}
              <div style={{ borderTop: "1px solid rgba(255,255,255,0.07)", padding: "14px 18px" }}>
                <div style={{
                  display: "flex", alignItems: "flex-end", gap: 10,
                  background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.1)",
                  borderRadius: 16, padding: "10px 12px",
                  transition: "border-color 0.2s",
                }}>
                  <textarea
                    ref={textareaRef}
                    value={query}
                    onChange={e => setQuery(e.target.value)}
                    onKeyDown={handleKey}
                    placeholder="Pose ta question ici… (Entrée pour envoyer)"
                    rows={1}
                    style={{
                      flex: 1, background: "transparent", border: "none", outline: "none",
                      fontSize: 13.5, lineHeight: 1.6, resize: "none",
                      maxHeight: 120, overflowY: "auto", fontFamily: "inherit",
                    }}
                  />
                  <button
                    className="send-btn"
                    onClick={handleSubmit}
                    disabled={!query.trim() || loading}
                    style={{
                      width: 36, height: 36, borderRadius: 11, border: "none", flexShrink: 0,
                      background: query.trim() && !loading ? "#2563eb" : "rgba(255,255,255,0.06)",
                      display: "flex", alignItems: "center", justifyContent: "center",
                      cursor: query.trim() && !loading ? "pointer" : "default",
                      transition: "all 0.2s",
                      boxShadow: query.trim() && !loading ? "0 4px 16px rgba(37,99,235,0.4)" : "none",
                    }}
                  >
                    {loading
                      ? <Loader2 size={15} color="#475569" style={{ animation: "spin 1s linear infinite" }}/>
                      : <Send size={14} color={query.trim() ? "#fff" : "#475569"}/>
                    }
                  </button>
                </div>
                <p style={{ textAlign: "center", fontSize: 10, color: "#1e293b", marginTop: 8 }}>
                  Sources : Radio Okapi · ACP · actualite.cd · et 9 autres · Shift+Entrée pour saut de ligne
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}