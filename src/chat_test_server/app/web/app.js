let conversationId = null;

const messagesEl = document.getElementById("messages");
const inputEl = document.getElementById("input");
const sendBtn = document.getElementById("send");

function addMessage(text, role) {
  const div = document.createElement("div");
  div.className = `message ${role}`;
  div.innerText = text;
  messagesEl.appendChild(div);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function downloadBlob(blob, filename) {
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename || "document.docx";
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(url);
}

async function sendMessage() {
  const text = inputEl.value.trim();
  if (!text) return;

  addMessage(text, "user");
  inputEl.value = "";

  try {
    const response = await fetch("/api/v1/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        message: text,
        conversation_id: conversationId,
      }),
    });

    const headerConversationId = response.headers.get("x-conversation-id");
    if (headerConversationId) {
      conversationId = headerConversationId;
    }

    const contentType = (response.headers.get("content-type") || "").toLowerCase();

    if (!response.ok) {
      const errorText = await response.text();
      addMessage(`Ошибка: ${errorText}`, "bot");
      return;
    }

    if (contentType.includes("application/vnd.openxmlformats-officedocument.wordprocessingml.document")) {
      const blob = await response.blob();
      downloadBlob(blob, `${conversationId || "document"}.docx`);
      addMessage("Документ готов. Скачивание началось.", "bot");
      return;
    }

    const data = await response.json();

    conversationId = data.conversation_id;
    addMessage(data.reply || "(пустой ответ)", "bot");
  } catch (err) {
    console.error(err);
    addMessage("Ошибка при отправке сообщения.", "bot");
  }
}

sendBtn.onclick = sendMessage;

inputEl.addEventListener("keypress", (e) => {
  if (e.key === "Enter") {
    sendMessage();
  }
});