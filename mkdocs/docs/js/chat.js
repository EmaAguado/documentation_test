document.addEventListener("DOMContentLoaded", async function () {
  let funnyMessages;
  try {
    const module = await import("./chat_error_messages.js");
    funnyMessages = module.errorMessages;
  } catch (error) {
    funnyMessages = ["Ups, algo salió mal. 🤖", "No encuentro mi respuesta. 😅"];
  }
  
  let pauseMessages;
  try {
    const pauseModule = await import("./chat_pause_messages.js");
    pauseMessages = pauseModule.pauseMessages;
  } catch (error) {
    pauseMessages = ["Ups, se ha pausado la generación. 🤖"];
  }
  
  // Guarda el último mensaje del usuario para reintentar
  let lastUserMessage = "";
  
  function processMessageText(text) {
    return text.replace(/(https?:\/\/\S+?\.gif)(\s|$)/gi,
      '<img src="$1" alt="GIF" style="max-width:100%; display:block; margin-top:10px;">$2');
  }
  function simpleMarkdownToHtml(text) {
    return text ? text.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
      .replace(/\*(.*?)\*/g, "<em>$1</em>")
      .replace(/__(.*?)__/g, "<u>$1</u>")
      .replace(/_(.*?)_/g, "<i>$1</i>")
      .replace(/\n/g, "<br>") : "";
  }
  function formatTimestamp(date) {
    const now = new Date(), opts = { hour: "2-digit", minute: "2-digit" };
    return date.toDateString() === now.toDateString() 
      ? "Hoy " + date.toLocaleTimeString([], opts) 
      : date.toLocaleDateString() + " " + date.toLocaleTimeString([], opts);
  }
  function cleanHTML(raw) {
    return raw.replace(/\n/g, "").replace(/>\s+</g, "><").replace(/\s\s+/g, " ").trim();
  }
  
  let isProcessing = false, abortController = null,
      origSend = "✉️", stopSend = "⏹";
  
  if (!document.getElementById("chat-button")) {
    const btn = document.createElement("div");
    btn.id = "chat-button";
    btn.innerHTML = '<span style="font-size:28px;">🤖</span>';
    document.body.appendChild(btn);
    
    const popup = document.createElement("div");
    popup.id = "chat-popup";
    popup.innerHTML = `
      <header>
        <span>MondoBot</span>
        <div>
          <button id="enlarge-chat" title="Ampliar chat">&#x26F6;</button>
          <span id="close-chat" style="cursor:pointer;" title="Cerrar chat">&times;</span>
        </div>
      </header>
      <div class="content" id="chat-content"></div>
      <footer>
        <div id="chat-input-container">
          <div id="chat-input" contenteditable="true" placeholder="Escribe tu mensaje..."></div>
          <button id="send-chat" title="Enviar"><i class="material-icons">${origSend}</i></button>
        </div>
      </footer>`;
    document.body.appendChild(popup);
    
    const chatContainer = document.getElementById("chat-content");
    let autoScrollChat = true;
    chatContainer.addEventListener("scroll", () => {
      autoScrollChat = (chatContainer.scrollTop + chatContainer.clientHeight >= chatContainer.scrollHeight - 5);
    });
    
    function togglePopup() { popup.classList.toggle("open"); }
    btn.addEventListener("click", togglePopup);
    document.getElementById("close-chat").addEventListener("click", togglePopup);
    document.getElementById("enlarge-chat").addEventListener("click", () => { popup.classList.toggle("enlarged"); });
    
    // Si el tipo es "pause", se inyecta la clase para fondo naranja en el CSS (defínela en tu hoja de estilos)
    function addMessage(sender, text, type = "MondoBot", id = null) {
      const now = new Date(), timestamp = formatTimestamp(now),
            raw = `
        <div class="chat-message ${type}" ${id ? `id="${id}"` : ""}>
          <div class="message-info"><span class="sender">${sender}</span> • <span class="timestamp">${timestamp}</span></div>
          <div class="message-content">${simpleMarkdownToHtml(processMessageText(text))}</div>
        </div>`;
      chatContainer.innerHTML += cleanHTML(raw);
      if (autoScrollChat) chatContainer.scrollTop = chatContainer.scrollHeight;
    }
    
    function createThinkingMessage(id) {
      const now = new Date(), timestamp = formatTimestamp(now),
            raw = `
        <div class="chat-message bot" id="${id}">
          <div class="message-info">
            <span class="sender">MondoBot</span> • <span class="timestamp">${timestamp}</span>
          </div>
          <div class="message-content">
            <div class="think-subwidget">
              <div class="think-header">
                <span class="think-title">Pensando...</span>
                <button class="toggle-think-text">></button>
              </div>
              <div class="think-text-collapsed collapsed"></div>
            </div>
            <div class="normal-text-subwidget"></div>
          </div>
        </div>`;
      chatContainer.innerHTML += cleanHTML(raw);
      if (autoScrollChat) chatContainer.scrollTop = chatContainer.scrollHeight;
    }
    
    function addBotMessageSplit(fullText) {
      let thinkPart = "", normalPart = fullText,
          match = /<think>([\s\S]*?)<\/think>/i.exec(fullText);
      if (match) { thinkPart = match[1]; normalPart = fullText.replace(match[0], ""); }
      const now = new Date(), timestamp = formatTimestamp(now),
            raw = `
        <div class="chat-message bot">
          <div class="message-info">
            <span class="sender">MondoBot</span> • <span class="timestamp">${timestamp}</span>
          </div>
          <div class="message-content">
            <div class="normal-text-subwidget">
              ${simpleMarkdownToHtml(processMessageText(normalPart))}
            </div>
          </div>
        </div>`;
      chatContainer.innerHTML += cleanHTML(raw);
      if (autoScrollChat) chatContainer.scrollTop = chatContainer.scrollHeight;
    }
    
    async function sendMessage() {
      // Si ya se está generando, se considera como "stop"
      if (isProcessing) {
        if (abortController) { 
          abortController.abort(); 
        }
        document.querySelector(".chat-message.bot")?.remove();
        isProcessing = false;
        document.getElementById("send-chat").querySelector("i").textContent = origSend;
        const randomPause = pauseMessages[Math.floor(Math.random() * pauseMessages.length)];
        addMessage("MondoBot", randomPause, "pause");
        const pauseMsgEl = document.querySelector(".chat-message.pause");
        if (pauseMsgEl) {
          const retryBtn = document.createElement("button");
          retryBtn.textContent = "Reintentar";
          // Asignar la clase para que se estilice desde CSS
          retryBtn.classList.add("retry-button");
          retryBtn.addEventListener("click", () => {
            document.getElementById("chat-input").innerText = lastUserMessage;
            pauseMsgEl.remove();
            sendMessage();
          });
          const msgContent = pauseMsgEl.querySelector(".message-content");
          // Inserta el botón como último elemento, fuera del contenido anterior
          msgContent.insertAdjacentElement("beforeend", retryBtn);
        }
        return;
      }    
      const chatInput = document.getElementById("chat-input"),
            sendBtnIcon = document.getElementById("send-chat").querySelector("i"),
            message = chatInput.innerText;
      if (!message.trim()) return;
      // Guarda el último mensaje del usuario
      lastUserMessage = message;
      isProcessing = true;
      abortController = new AbortController();
      const signal = abortController.signal;
      sendBtnIcon.textContent = stopSend;
      addMessage("Yo", message, "user");
      chatInput.innerText = "";
      const currentThinkingId = `thinking-msg-${Date.now()}`;
      createThinkingMessage(currentThinkingId);
      const thinkingEl = document.getElementById(currentThinkingId);
      let autoScrollThink = true;
      const thinkTextContainer = thinkingEl.querySelector(".think-text-collapsed");
      thinkTextContainer.addEventListener("scroll", () => {
        autoScrollThink = (thinkTextContainer.scrollTop + thinkTextContainer.clientHeight >= thinkTextContainer.scrollHeight - 5);
      });
      const toggleBtn = thinkingEl.querySelector(".toggle-think-text");
      toggleBtn.addEventListener("click", () => {
        if (thinkTextContainer.classList.contains("collapsed")) { 
          thinkTextContainer.classList.remove("collapsed"); 
          toggleBtn.textContent = "v";
        } else { 
          thinkTextContainer.classList.add("collapsed"); 
          toggleBtn.textContent = ">";
        }
      });
      let compiledResponse = "", thinkingUpdated = false;
      try {
        const response = await fetch("http://localhost:11434/api/generate", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ model: "deepseek-r1:7b", prompt: JSON.stringify({ message }) }),
          signal
        });
        if (!response.ok) throw new Error("No se pudo conectar con el LLM");
        const reader = response.body.getReader(), decoder = new TextDecoder();
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          const chunk = decoder.decode(value, { stream: true });
          let chunkJson = JSON.parse(chunk);
          compiledResponse += chunkJson.response;
          compiledResponse = compiledResponse.replace(/\n/g, "");
          let thinkPart = "", normalPart = compiledResponse;
          if (compiledResponse.includes("<think>")) {
            const start = compiledResponse.indexOf("<think>"),
                  end = compiledResponse.indexOf("</think>");
            if (end !== -1) { 
              thinkPart = compiledResponse.substring(start + 7, end);
              normalPart = compiledResponse.substring(0, start) + compiledResponse.substring(end + 8);
            } else { 
              thinkPart = compiledResponse.substring(start + 7);
              normalPart = compiledResponse.substring(0, start);
            }
          }
          const processedThink = simpleMarkdownToHtml(processMessageText(thinkPart)),
                processedNormal = simpleMarkdownToHtml(processMessageText(normalPart));
          if (thinkingEl) {
            thinkingEl.querySelector(".think-text-collapsed").innerHTML = processedThink;
            thinkingEl.querySelector(".normal-text-subwidget").innerHTML = processedNormal;
            thinkingEl.querySelector(".think-header .think-title").textContent = "Pensando...";
            if (autoScrollThink) thinkTextContainer.scrollTop = thinkTextContainer.scrollHeight;
            if (autoScrollChat) chatContainer.scrollTop = chatContainer.scrollHeight;
            if (!thinkingUpdated) {
              thinkingEl.querySelector(".message-content").classList.remove("pensando");
              thinkingEl.querySelector(".message-content").classList.add("thinking-fade");
              thinkingUpdated = true;
            }
          }
        }
        thinkingEl?.remove();
        addBotMessageSplit(compiledResponse);
      } catch (error) {
        if (error.name === "AbortError") return;
        document.getElementById(currentThinkingId)?.remove();
        const randomMsg = funnyMessages[Math.floor(Math.random() * funnyMessages.length)];
        addMessage("MondoBot", `<span style="display:block; background-color: var(--chat-error-bg); padding: 5px; border-radius: 4px;">${randomMsg}</span>`, "error");
      } finally {
        isProcessing = false;
        abortController = null;
        sendBtnIcon.textContent = origSend;
      }
    }
    document.getElementById("send-chat").addEventListener("click", sendMessage);
    document.getElementById("chat-input").addEventListener("keydown", e => { 
      if (e.key === "Enter" && !e.shiftKey) { 
        e.preventDefault(); 
        sendMessage(); 
      } 
    });
  }
});
