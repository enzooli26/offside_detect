"use strict";
const $ = id => document.getElementById(id);
const labels = {
  onside: ["未发现越位位置", ""], offside_receiver: ["越位接球候选", "danger"],
  offside_interference: ["干扰概率达阈值 · 待复核", "warn"],
  potential_interference: ["疑似干扰 · 待复核", "warn"],
  position_uncertain: ["位置不确定", "warn"],
  insufficient_defensive_visibility: ["防线不完整", "neutral"],
  insufficient_ball_position: ["球位置不足", "neutral"]
};
let busy = false, pollTimer, lastResult = null, selected = 0, currentId = null;
function feedback(message, error = false) {
  $("feedback").textContent = message;
  $("feedback").classList.toggle("error", error);
}
function setBusy(value) {
  busy = value;
  ["video", "calibration", "events", "threshold", "demo"].forEach(id => $(id).disabled = value);
  $("generate").disabled = value || !["video", "calibration", "events"].every(id => $(id).files.length);
  $("generate").textContent = value ? "正在处理，请稍候…" : "生成鸟瞰结果 →";
}
async function api(url, options = {}) {
  const response = await fetch(url, options);
  let data;
  try { data = await response.json(); } catch { throw new Error("服务返回异常，请重新打开工作台。"); }
  if (!response.ok) throw new Error(data.error || "请求失败");
  return data;
}
function progress(value, text) {
  $("progress-wrap").hidden = false;
  $("progress").value = value;
  $("progress-number").textContent = `${value}%`;
  $("progress-label").textContent = text;
}
function resetResult() {
  lastResult = null;
  $("result-image").hidden = true; $("placeholder").toggleAttribute("hidden", false);
  $("view-state").textContent = "生成中"; $("view-state").classList.remove("ready");
  $("event-list").replaceChildren();
  const row = $("event-list").insertRow(); const cell = row.insertCell();
  cell.colSpan = 6; cell.className = "empty"; cell.textContent = "正在准备新一份分析…";
  $("event-count").textContent = "0 个事件";
  ["download-video", "download-report"].forEach(id => {
    $(id).removeAttribute("href"); $(id).classList.add("disabled"); $(id).setAttribute("aria-disabled", "true");
  });
  $("source-details").hidden = true;
  $("frame-label").textContent = "EVENT FRAME / —";
  $("image-caption").textContent = "视图示意 · 等待新结果";
  $("result-title").textContent = "正在生成分析";
  $("result-description").textContent = "处理完成后显示实际事件帧。";
}
function fail(error) {
  clearTimeout(pollTimer); setBusy(false);
  feedback(error.message || String(error), true);
  $("view-state").textContent = "请检查输入";
  $("result-title").textContent = "本次分析未完成";
  $("result-description").textContent = "请根据左侧提示检查文件后重试。";
  localStorage.removeItem("offsideJob");
}
function upload(url, file, number) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest(); xhr.open("POST", url);
    xhr.upload.onprogress = event => { if (event.lengthComputable) progress(Math.round(event.loaded / event.total * 100), `正在导入 ${number}/3`); };
    xhr.onload = () => { if (xhr.status >= 200 && xhr.status < 300) resolve(); else { let text = "文件导入失败"; try { text = JSON.parse(xhr.responseText).error; } catch {} reject(new Error(text)); } };
    xhr.onerror = () => reject(new Error("连接中断，请确认本地工作台仍在运行。"));
    xhr.send(file);
  });
}
async function poll(id) {
  try {
    const job = await api(`/api/jobs/${id}`);
    progress(job.progress, job.message);
    feedback(job.message);
    if (job.status === "complete") {
      showResult(id, job.result); setBusy(false); return;
    }
    if (job.status === "failed") throw new Error(job.message);
    pollTimer = setTimeout(() => poll(id), 800);
  } catch (error) { fail(error); }
}
function formatTime(seconds) {
  const m = Math.floor(seconds / 60), s = (seconds % 60).toFixed(2).padStart(5, "0");
  return `${String(m).padStart(2, "0")}:${s}`;
}
function selectEvent(index) {
  selected = index;
  const event = lastResult.events[index]; const base = `/files/${currentId}/`;
  $("placeholder").toggleAttribute("hidden", true); $("result-image").hidden = false;
  $("result-image").src = base + event.preview;
  $("source-image").src = base + event.source;
  $("source-details").hidden = false;
  $("frame-label").textContent = `FRAME ${String(event.frame).padStart(6, "0")} / ${formatTime(event.time_seconds)}`;
  $("image-caption").textContent = `事件 ${String(index + 1).padStart(2, "0")} · ${(labels[event.status] || [event.status])[0]}`;
  $("result-title").textContent = (labels[event.status] || [event.status])[0];
  $("result-description").textContent = event.message;
  [...$("event-list").rows].forEach((row, i) => row.classList.toggle("selected", i === index));
}
function showResult(id, result) {
  currentId = id; lastResult = result;
  $("view-state").textContent = "已生成"; $("view-state").classList.add("ready");
  $("event-count").textContent = `${result.events.length} 个事件`;
  $("event-list").replaceChildren();
  result.events.forEach((event, i) => {
    const row = $("event-list").insertRow();
    const status = labels[event.status] || [event.status, "neutral"];
    [String(i + 1).padStart(2, "0"), formatTime(event.time_seconds), `# ${event.frame}`].forEach(text => { row.insertCell().textContent = text; });
    const badge = document.createElement("span"); badge.className = `badge ${status[1]}`; badge.textContent = status[0]; row.insertCell().append(badge);
    row.insertCell().textContent = event.offside_players.join("、") || "—";
    const button = document.createElement("button"); button.className = "text-button"; button.textContent = "查看 ↗";
    button.setAttribute("aria-label", `查看事件 ${i + 1}`); row.insertCell().append(button);
    row.onclick = () => selectEvent(i);
  });
  [["download-video", "analysis.mp4"], ["download-report", "report.json"]].forEach(([idName, name]) => {
    $(idName).href = `/files/${id}/${name}`; $(idName).classList.remove("disabled"); $(idName).setAttribute("aria-disabled", "false");
  });
  if (result.events.length) selectEvent(0);
  feedback(`完成 · ${result.frames_read} 帧 · ${result.events.length} 个事件。可点击事件复核并下载结果。`);
}
for (const id of ["video", "calibration", "events"]) {
  $(id).addEventListener("change", () => {
    const file = $(id).files[0];
    $(id === "video" ? "video-name" : `${id}-name`).textContent = file ? file.name : "尚未选择";
    if (id === "video" && file) $("video-detail").textContent = `${(file.size / 1024 / 1024).toFixed(1)} MB · 已选择`;
    setBusy(busy);
  });
}
$("video-drop").ondragover = event => { event.preventDefault(); if (!busy) $("video-drop").classList.add("dragging"); };
$("video-drop").ondragleave = () => $("video-drop").classList.remove("dragging");
$("video-drop").ondrop = event => {
  event.preventDefault(); $("video-drop").classList.remove("dragging");
  if (busy || event.dataTransfer.files.length !== 1) return;
  $("video").files = event.dataTransfer.files; $("video").dispatchEvent(new Event("change"));
};
$("threshold").oninput = () => $("threshold-value").textContent = Number($("threshold").value).toFixed(2);
$("generate").onclick = async () => {
  setBusy(true); resetResult();
  try {
    const created = await api("/api/jobs", {method: "POST"});
    for (const [index, kind] of ["video", "calibration", "events"].entries()) {
      await upload(`/api/jobs/${created.id}/${kind}`, $(kind).files[0], index + 1);
    }
    progress(0, "正在校验素材");
    await api(`/api/jobs/${created.id}/start`, {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({threshold: Number($("threshold").value)})});
    localStorage.setItem("offsideJob", created.id); poll(created.id);
  } catch (error) { fail(error); }
};
$("demo").onclick = async () => {
  setBusy(true); resetResult(); progress(0, "正在准备合成演示");
  try { const job = await api("/api/demo", {method: "POST"}); localStorage.setItem("offsideJob", job.id); poll(job.id); }
  catch (error) { fail(error); }
};
$("help").onclick = () => $("guide").showModal();
$("close-help").onclick = $("guide-done").onclick = () => $("guide").close();
$("stop").onclick = async () => {
  if (!confirm(busy ? "任务仍在处理中。关闭后任务会继续完成，但页面将断开。确定关闭工作台？" : "关闭本地工作台？再次双击启动文件即可打开。")) return;
  try {
    await api("/api/shutdown", {method: "POST"}); clearTimeout(pollTimer);
    document.body.replaceChildren(); const message = document.createElement("p"); message.className = "offline"; message.textContent = "工作台已关闭。再次双击「启动越位分析.vbs」即可打开。"; document.body.append(message);
  } catch (error) { feedback(error.message, true); }
};
const saved = localStorage.getItem("offsideJob");
if (saved) { setBusy(true); poll(saved); }
