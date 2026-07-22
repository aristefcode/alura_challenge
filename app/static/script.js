const form = document.getElementById("chat-form");
const input = document.getElementById("question");
const chat = document.getElementById("chat");
const newChatBtn = document.getElementById("new-chat");

const WELCOME_MESSAGE =
  "¡Hola! Soy el Alura Agente 👋 Puedo responder preguntas basadas en " +
  "los documentos internos que tengo indexados. ¿Qué quieres saber?";

function addMessage(text, role) {
  const bubble = document.createElement("div");
  bubble.className = `bubble ${role}`;
  bubble.textContent = text;
  chat.appendChild(bubble);
  chat.scrollTop = chat.scrollHeight;
  return bubble;
}

function addSources(sources) {
  if (!sources || sources.length === 0) return;

  const wrap = document.createElement("div");
  wrap.className = "sources";

  sources.forEach((s) => {
    const pill = document.createElement("span");
    pill.className = "source-pill";
    pill.textContent = `📄 ${s.file} · p.${s.page}`;
    wrap.appendChild(pill);
  });

  chat.appendChild(wrap);
  chat.scrollTop = chat.scrollHeight;
}

function parseSourcesHeader(response) {
  const raw = response.headers.get("X-Sources");
  if (!raw) return [];
  try {
    return JSON.parse(decodeURIComponent(raw));
  } catch (err) {
    return [];
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const question = input.value.trim();
  if (!question) return;

  addMessage(question, "user");
  input.value = "";
  input.disabled = true;

  const assistantBubble = addMessage("", "assistant");
  assistantBubble.classList.add("typing");

  try {
    const response = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: `question=${encodeURIComponent(question)}`,
    });

    if (!response.ok || !response.body) {
      throw new Error("Respuesta inválida del servidor");
    }

    const sources = parseSourcesHeader(response);

    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let fullText = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      fullText += decoder.decode(value, { stream: true });
      assistantBubble.textContent = fullText;
      chat.scrollTop = chat.scrollHeight;
    }

    assistantBubble.classList.remove("typing");
    addSources(sources);
  } catch (err) {
    assistantBubble.classList.remove("typing");
    assistantBubble.textContent = "❌ Ocurrió un error al conectar con el agente. Intenta de nuevo.";
  } finally {
    input.disabled = false;
    input.focus();
  }
});

newChatBtn.addEventListener("click", async () => {
  try {
    await fetch("/reset", { method: "POST" });
  } catch (err) {
    // Si falla el reset en el servidor, igual limpiamos la vista local.
  }

  chat.innerHTML = "";
  addMessage(WELCOME_MESSAGE, "assistant");
  input.value = "";
  input.focus();
});
