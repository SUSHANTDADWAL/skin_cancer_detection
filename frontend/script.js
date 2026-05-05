const BASE_URL = "http://127.0.0.1:5000";

function showPopup(message, success = true) {
  Swal.fire({
    icon: success ? "success" : "error",
    title: message,
    timer: 2000,
    showConfirmButton: false
  });
}


function login() {
  fetch(`${BASE_URL}/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({
      username: document.getElementById("username").value,
      password: document.getElementById("password").value
    })
  })
  .then(res => res.json())
  .then(data => {
    showPopup(data.message, data.message === "Login successful");

    if (data.message === "Login successful") {
      setTimeout(() => {
        window.location.href = `${BASE_URL}/index`;
      }, 1000);
    }
  })
  .catch(() => showPopup("Login failed", false));
}

function signup() {
  fetch(`${BASE_URL}/signup`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({
      username: document.getElementById("username").value,
      password: document.getElementById("password").value
    })
  })
  .then(res => res.json())
  .then(data => {
    showPopup(data.message);

    if (data.message === "Signup successful") {
      setTimeout(() => {
        window.location.href = "login.html";
      }, 1000);
    }
  })
  .catch(() => showPopup("Signup failed", false));
}

function upload() {
  let file = document.getElementById("file").files[0];

  const loader = document.getElementById("loader");
  const text = document.getElementById("loadingText");
  const box = document.getElementById("resultBox");
  const resultEl = document.getElementById("result");
  const btn = document.getElementById("predictBtn");

  if (!file) {
    showPopup("Please select an image", false);
    return;
  }

  let formData = new FormData();
  formData.append("file", file);

  btn.disabled = true;
  loader.style.display = "block";
  text.style.display = "block";
  box.style.display = "none";

  fetch(`${BASE_URL}/predict`, {
    method: "POST",
    body: formData,
    credentials: "include"
  })
  .then(res => {
    if (res.status === 401) {
      window.location.href = "login.html";
      return;
    }
    return res.json();
  })
  .then(data => {

    loader.style.display = "none";
    text.style.display = "none";
    btn.disabled = false;

    box.style.display = "block";

    let resultHTML = `
      <h3>${data.prediction === "Malignant" ? "⚠️ Malignant" : "✅ Benign"}</h3>
      <p><strong>Confidence:</strong> ${data.confidence}</p>
      <p><strong>Risk:</strong> ${data.risk}</p>
      <p>${data.explanation}</p>

      <button class="pdf-btn" onclick='downloadPDF(${JSON.stringify(data)})'>
        📄 Download Report
      </button>
    `;

    resultEl.innerHTML = resultHTML;

    if (data.prediction === "Malignant") {
      box.className = "result-box red";
    } else {
      box.className = "result-box green";
    }

    showPopup("Prediction completed");
  })
  .catch(() => {
    loader.style.display = "none";
    text.style.display = "none";
    btn.disabled = false;
    showPopup("Prediction failed", false);
  });
}

function logout() {
  fetch(`${BASE_URL}/logout`, {
    method: "GET",
    credentials: "include"
  })
  .then(res => res.json())
  .then(() => {
    showPopup("Logged out successfully");

    setTimeout(() => {
      window.location.href = "login.html";
    }, 1000);
  })
  .catch(() => showPopup("Logout failed", false));
}

function goToHistory() {
  window.location.href = `${BASE_URL}/history-page`;
}
function loadHistory() {
  const riskFilter = document.getElementById("riskFilter").value;
  const dateFilter = document.getElementById("dateFilter").value;

  fetch(`${BASE_URL}/history`, {
    credentials: "include"
  })
  .then(res => {
    if (res.status === 401) {
      window.location.href = "login.html";
      return;
    }
    return res.json();
  })
  .then(data => {

    const container = document.getElementById("historyContainer");
    container.innerHTML = "";

    let filtered = data.filter(item => {

      if (riskFilter !== "all" && item.risk !== riskFilter) return false;

      if (dateFilter) {
        let itemDate = new Date(item.date).toISOString().split("T")[0];
        if (itemDate !== dateFilter) return false;
      }

      return true;
    });

    if (filtered.length === 0) {
      container.innerHTML = "<p style='text-align:center;'>No records found</p>";
      return;
    }

    filtered.forEach((item, index) => {

      const card = document.createElement("div");
      card.className = `history-card ${item.risk.toLowerCase()}`;

      card.style.animationDelay = `${index * 0.1}s`;

      card.innerHTML = `
        <h3>${item.prediction === "Malignant" ? "⚠️ Malignant" : "✅ Benign"}</h3>
        <p><strong>Confidence:</strong> ${(item.confidence * 100).toFixed(2)}%</p>
        <p><strong>Risk:</strong> ${item.risk}</p>
        <p><strong>Date:</strong> ${new Date(item.date).toLocaleString()}</p>
        <p>${item.explanation}</p>

        <button class="pdf-btn">📄 Download Report</button>
      `;

      card.querySelector(".pdf-btn").addEventListener("click", () => {
        downloadPDF({
          prediction: item.prediction,
          confidence: (item.confidence * 100).toFixed(2) + "%",
          risk: item.risk,
          explanation: item.explanation
        });
      });

      container.appendChild(card);
    });

  })
  .catch(() => {
    showPopup("Failed to load history", false);
  });
}

function downloadPDF(data) {
  const fileInput = document.getElementById("file");
  const file = fileInput ? fileInput.files[0] : null;

  if (file) {
    const reader = new FileReader();

    reader.onload = function () {
      fetch(`${BASE_URL}/download-report`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        credentials: "include",
        body: JSON.stringify({
          ...data,
          image: reader.result
        })
      })
      .then(res => res.blob())
      .then(blob => {
        const url = window.URL.createObjectURL(blob);
        window.open(url);
      });
    };

    reader.readAsDataURL(file);

  } else {
    fetch(`${BASE_URL}/download-report`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      credentials: "include",
      body: JSON.stringify(data)
    })
    .then(res => res.blob())
    .then(blob => {
      const url = window.URL.createObjectURL(blob);
      window.open(url);
    });
  }
}