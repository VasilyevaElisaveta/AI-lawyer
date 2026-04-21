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

async function sendMessage() {
  const text = inputEl.value.trim();
  if (!text) return;

  addMessage(text, "user");
  inputEl.value = "";

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

  const data = await response.json();

  conversationId = data.conversation_id;
  addMessage(data.reply, "bot");
}

sendBtn.onclick = sendMessage;

inputEl.addEventListener("keypress", (e) => {
  if (e.key === "Enter") {
    sendMessage();
  }
});