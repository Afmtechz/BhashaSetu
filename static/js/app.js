const $=id=>document.getElementById(id);let teacherSocket,studentSocket,audioContext,processor,microphone,stream,started=false,startAt=0,timer;
document.querySelectorAll("[data-nav]").forEach(b=>b.onclick=event=>{event.preventDefault();document.querySelectorAll(".view").forEach(v=>v.classList.remove("active"));$("view-"+b.dataset.nav).classList.add("active");window.scrollTo({top:0,behavior:"instant" in window?"instant":"auto"})});
const configuredBackend=new URLSearchParams(location.search).get("backend")||location.origin;
const backendUrl=configuredBackend.replace(/\/+$/,"");
const wsBase=backendUrl.startsWith("https:")?backendUrl.replace(/^https:/,"wss:"):backendUrl.replace(/^http:/,"ws:");
function err(el,e){el.textContent=e.message||String(e);el.className="status error"}
function pcm(f){let o=new Int16Array(f.length);for(let i=0;i<f.length;i++){let s=Math.max(-1,Math.min(1,f[i]));o[i]=s<0?s*32768:s*32767}return new Uint8Array(o.buffer)}
function down(a,r){if(r===16000)return pcm(a);let q=r/16000,n=Math.round(a.length/q),o=new Float32Array(n);for(let i=0;i<n;i++){let s=Math.floor(i*q),e=Math.min(Math.floor((i+1)*q),a.length),t=0;for(let j=s;j<e;j++)t+=a[j];o[i]=t/Math.max(1,e-s)}return pcm(o)}
function b64(a){let x="",n=0x8000;for(let i=0;i<a.length;i+=n)x+=String.fromCharCode(...a.subarray(i,i+n));return btoa(x)}
function addLine(text,interim){let box=$("teacherTranscript"),empty=box.querySelector(".status");if(empty)empty.remove();let old=box.querySelector("[data-interim]");if(old)old.remove();let div=document.createElement("div");div.className="line";div.dataset.interim=interim?"1":"";div.textContent=text+(interim?" ...":"");box.appendChild(div);box.scrollTop=box.scrollHeight}
async function start(){if(!navigator.mediaDevices?.getUserMedia)throw Error("This browser cannot use the microphone. Open the HTTPS address.");stream=await navigator.mediaDevices.getUserMedia({audio:true});teacherSocket=new WebSocket(`${wsBase}/ws/teacher`);teacherSocket.onmessage=async e=>{let m=JSON.parse(e.data);if(m.type==="connecting")$("micLabel").textContent="Connecting to Sarvam";if(m.type==="ready"){$("micLabel").textContent="Listening";$("setupStatus").textContent="";}if(m.type==="transcript_partial")addLine(m.text,true);if(m.type==="transcript_final"){addLine(m.text,false);let old=$("studentHistory");}if(m.type==="error")err($("setupStatus"),Error(m.message))};teacherSocket.onerror=()=>err($("setupStatus"),Error("Cannot connect to backend. Is FastAPI running at this address?"));teacherSocket.onclose=()=>{if(started){started=false;$("micLabel").textContent="Disconnected"}};await new Promise((res,rej)=>{teacherSocket.onopen=res;teacherSocket.onerror=()=>rej(Error("Cannot connect to backend. Is FastAPI running at this address?"))});audioContext=new AudioContext();microphone=audioContext.createMediaStreamSource(stream);processor=audioContext.createScriptProcessor(4096,1,1);processor.onaudioprocess=e=>{if(teacherSocket.readyState===1)teacherSocket.send(JSON.stringify({type:"audio",audio:b64(down(e.inputBuffer.getChannelData(0),audioContext.sampleRate))}))};microphone.connect(processor);processor.connect(audioContext.destination);started=true;startAt=Date.now();$("teacherSetup").style.display="none";$("teacherLive").style.display="block";timer=setInterval(()=>{let s=Math.floor((Date.now()-startAt)/1000);$("teacherTimer").textContent=String(Math.floor(s/60)).padStart(2,"0")+":"+String(s%60).padStart(2,"0")},1000)}
async function stop(){started=false;clearInterval(timer);processor?.disconnect();microphone?.disconnect();stream?.getTracks().forEach(t=>t.stop());await audioContext?.close();if(teacherSocket?.readyState===1)teacherSocket.send(JSON.stringify({type:"stop"}));teacherSocket?.close();$("teacherLive").style.display="none";$("teacherSummary").style.display="block"}
$("startLectureBtn").onclick=()=>start().catch(e=>err($("setupStatus"),e));$("endLectureBtn").onclick=stop;$("teacherRestartBtn").onclick=()=>location.reload();
$("joinClassBtn").onclick=()=>{studentSocket?.close();studentSocket=new WebSocket(`${wsBase}/ws/student`);studentSocket.onopen=()=>{studentSocket.send(JSON.stringify({type:"join",language:$("studentLang").value}));$("studentJoinStatus").textContent="Connected â€” waiting for teacher";$("studentJoin").style.display="none";$("studentLive").style.display="block"};studentSocket.onerror=()=>err($("studentJoinStatus"),Error("Cannot connect to backend. Is FastAPI running at this address?"));studentSocket.onmessage=async e=>{let m=JSON.parse(e.data);if(m.type==="subtitle"){$("studentCurrentLine").textContent=m.translated;$("studentCurrentLine").className="subtitle "+($("studentLang").value==="te"?"te":"hi");let h=document.createElement("div");h.textContent=m.translated;h.className=$("studentLang").value==="te"?"te":"hi";$("studentHistory").appendChild(h);let bytes=Uint8Array.from(atob(m.audio_base64),c=>c.charCodeAt(0));await new Audio(URL.createObjectURL(new Blob([bytes],{type:"audio/wav"}))).play()}if(m.type==="error")err($("studentJoinStatus"),Error(m.message))}}

let teacherPeer, studentPeer, studentIceQueue = [], teacherClassCode = "";
function signal(message) {
  if (teacherSocket && teacherSocket.readyState === WebSocket.OPEN) {
    teacherSocket.send(JSON.stringify({type:"signal", signal:message}));
  }
}
function makePeer(iceHandler) {
  const peer = new RTCPeerConnection({iceServers:[{urls:"stun:stun.l.google.com:19302"}]});
  peer.onicecandidate = event => { if (event.candidate) iceHandler(event.candidate); };
  return peer;
}
async function startVideoForStudent() {
  if (!teacherPeer || !stream) return;
  teacherPeer.addTrack(stream.getVideoTracks()[0], stream);
  const offer = await teacherPeer.createOffer();
  await teacherPeer.setLocalDescription(offer);
  signal({kind:"offer", description:teacherPeer.localDescription});
}
async function startWithVideo() {
  if (!navigator.mediaDevices?.getUserMedia) throw Error("This browser cannot use the microphone or camera. Open the HTTPS address.");
  stream = await navigator.mediaDevices.getUserMedia({audio:true, video:true});
  $("teacherVideo").srcObject = stream;
  teacherSocket = new WebSocket(`${wsBase}/ws/teacher`);
  teacherSocket.onmessage = async event => {
    const m = JSON.parse(event.data);
    if (m.type === "connecting") $("micLabel").textContent = "Connecting to Sarvam";
    if (m.type === "ready") { $("micLabel").textContent = "Listening"; $("setupStatus").textContent = ""; }
    if (m.type === "student_ready") {
      teacherPeer = makePeer(candidate => signal({kind:"candidate", candidate}));
      await startVideoForStudent();
    }
    if (m.type === "signal" && m.signal?.kind === "answer") {
      await teacherPeer.setRemoteDescription(m.signal.description);
    }
    if (m.type === "signal" && m.signal?.kind === "candidate" && teacherPeer) {
      await teacherPeer.addIceCandidate(m.signal.candidate);
    }
    if (m.type === "transcript_partial") addLine(m.text, true);
    if (m.type === "transcript_final") addLine(m.text, false);
    if (m.type === "error") err($("setupStatus"), Error(m.message));
  };
  teacherSocket.onerror = () => err($("setupStatus"), Error("Cannot connect to backend. Is FastAPI running at this address?"));
  await new Promise((resolve, reject) => {
    teacherSocket.onopen = resolve;
    teacherSocket.onerror = () => reject(Error("Cannot connect to backend. Is FastAPI running at this address?"));
  });
  audioContext = new AudioContext();
  microphone = audioContext.createMediaStreamSource(stream);
  processor = audioContext.createScriptProcessor(4096,1,1);
  processor.onaudioprocess = event => {
    if (teacherSocket.readyState === 1) teacherSocket.send(JSON.stringify({type:"audio",audio:b64(down(event.inputBuffer.getChannelData(0),audioContext.sampleRate))}));
  };
  microphone.connect(processor); processor.connect(audioContext.destination);
  started = true; startAt = Date.now();
  $("teacherSetup").style.display="none"; $("teacherLive").style.display="block";
  timer = setInterval(() => { const s=Math.floor((Date.now()-startAt)/1000); $("teacherTimer").textContent=String(Math.floor(s/60)).padStart(2,"0")+":"+String(s%60).padStart(2,"0"); },1000);
}
async function stopWithVideo() {
  started=false; clearInterval(timer); teacherPeer?.close(); teacherPeer=null;
  processor?.disconnect(); microphone?.disconnect(); stream?.getTracks().forEach(track=>track.stop());
  await audioContext?.close();
  $("statStudents").textContent=String(studentsReached);
  if (teacherSocket?.readyState===1) teacherSocket.send(JSON.stringify({type:"stop"}));
  teacherSocket?.close(); $("teacherVideo").srcObject=null;
  $("teacherLive").style.display="none"; $("teacherSummary").style.display="block";
}
$("startLectureBtn").onclick = () => startWithVideo().catch(e => err($("setupStatus"),e));
$("endLectureBtn").onclick = stopWithVideo;
$("joinClassBtn").onclick = () => {
  studentSocket?.close();
  studentSocket = new WebSocket(`${wsBase}/ws/student`);
  studentPeer = makePeer(candidate => studentSocket.send(JSON.stringify({type:"signal",signal:{kind:"candidate",candidate}})));
  studentPeer.ontrack = event => { $("studentVideo").srcObject = event.streams[0]; };
  studentPeer.oniceconnectionstatechange = () => {
    if (["failed","disconnected"].includes(studentPeer.iceConnectionState)) $("studentJoinStatus").textContent = "Video connection lost";
  };
  studentSocket.onopen = () => {
    studentSocket.send(JSON.stringify({type:"join",language:$("studentLang").value}));
    studentSocket.send(JSON.stringify({type:"student_ready"}));
    $("studentJoinStatus").textContent="Connected â€” waiting for teacher";
    $("studentJoin").style.display="none"; $("studentLive").style.display="block";
  };
  studentSocket.onerror = () => err($("studentJoinStatus"),Error("Cannot connect to backend. Is FastAPI running at this address?"));
  studentSocket.onmessage = async event => {
    const m=JSON.parse(event.data);
    if (m.type === "signal" && m.signal?.kind === "offer") {
      await studentPeer.setRemoteDescription(m.signal.description);
      for (const candidate of studentIceQueue) await studentPeer.addIceCandidate(candidate);
      studentIceQueue=[];
      const answer=await studentPeer.createAnswer();
      await studentPeer.setLocalDescription(answer);
      studentSocket.send(JSON.stringify({type:"signal",signal:{kind:"answer",description:studentPeer.localDescription}}));
    }
    if (m.type === "signal" && m.signal?.kind === "candidate") {
      if (studentPeer.remoteDescription) await studentPeer.addIceCandidate(m.signal.candidate);
      else studentIceQueue.push(m.signal.candidate);
    }
    if (m.type === "subtitle") {
      $("studentCurrentLine").textContent=m.translated;
      $("studentCurrentLine").className="subtitle "+($("studentLang").value==="te"?"te":"hi");
      const h=document.createElement("div"); h.textContent=m.translated; h.className=$("studentLang").value==="te"?"te":"hi"; $("studentHistory").appendChild(h);
      const bytes=Uint8Array.from(atob(m.audio_base64),c=>c.charCodeAt(0));
      const audio=new Audio(URL.createObjectURL(new Blob([bytes],{type:"audio/wav"})));
      audio.dataset.segmentId=m.segment_id; await audio.play();
    }
    if (m.type === "error") err($("studentJoinStatus"),Error(m.message));
  };
};

let teacherMuted=false, studentMuted=false, currentAudio=null, speakingAllowed=false, studentsReached=0;
function updateStudents(message) {
  if (!message || message.type !== "students") return;
  studentsReached = message.count;
  $("studentCount").textContent=message.count;
  $("studentNames").textContent=message.names.length ? message.names.join(", ") : "No students connected.";
}
function showSpeakRequest(name) {
  const box=$("speakRequests"), row=document.createElement("div");
  row.style.marginTop="8px";
  row.innerHTML=`<strong>${name}</strong> wants to speak <button class="btn primary" style="padding:6px 10px;margin-left:8px">Allow</button>`;
  row.querySelector("button").onclick=()=>{teacherSocket.send(JSON.stringify({type:"accept_speak",name}));row.innerHTML=`<strong>${name}</strong> is allowed to speak.`};
  box.textContent=""; box.appendChild(row);
}
function handleTeacherMessage(m) {
  updateStudents(m);
  if(m.type==="student_ready" && stream) {
    teacherPeer = makePeer(candidate => signal({kind:"candidate", candidate}));
    teacherPeer.addTrack(stream.getVideoTracks()[0], stream);
    teacherPeer.createOffer().then(offer => teacherPeer.setLocalDescription(offer)).then(() => signal({kind:"offer", description:teacherPeer.localDescription}));
  }
  if(m.type==="speak_request") showSpeakRequest(m.name);
  if(m.type==="student_speech") {
    addLine(`${m.name}: ${m.original} â†’ ${m.translated}`, false);
  }
}
async function startWithVideoAndControls() {
  const classResponse = await fetch(`${backendUrl}/api/classes`, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({name: $("className").value})
  });
  if (!classResponse.ok) throw Error("Could not create the classroom.");
  const classDetails = await classResponse.json();
  teacherClassCode = classDetails.code;
  $("teacherClassLabel").textContent = `${classDetails.name} · ${teacherClassCode}`;
  $("classCodeStatus").textContent = `Share class code ${teacherClassCode} with your students.`;
  stream=await navigator.mediaDevices.getUserMedia({audio:true,video:true});
  $("teacherVideo").srcObject=stream;
  teacherSocket=new WebSocket(`${wsBase}/ws/teacher`);
  teacherSocket.onmessage=e=>{const m=JSON.parse(e.data);handleTeacherMessage(m);if(m.type==="connecting")$("micLabel").textContent="Connecting to Sarvam";if(m.type==="ready")$("micLabel").textContent="Listening";if(m.type==="transcript_partial")addLine(m.text,true);if(m.type==="transcript_final")addLine(m.text,false);if(m.type==="signal"&&m.signal?.kind==="answer")teacherPeer?.setRemoteDescription(m.signal.description);if(m.type==="signal"&&m.signal?.kind==="candidate"&&teacherPeer)teacherPeer.addIceCandidate(m.signal.candidate);};
  await new Promise((resolve,reject)=>{teacherSocket.onopen=()=>{teacherSocket.send(JSON.stringify({type:"teacher_join",code:teacherClassCode}));resolve()};teacherSocket.onerror=()=>reject(Error("Cannot connect to the classroom server."))});
  audioContext=new AudioContext();microphone=audioContext.createMediaStreamSource(stream);processor=audioContext.createScriptProcessor(4096,1,1);processor.onaudioprocess=e=>{if(teacherSocket.readyState===1)teacherSocket.send(JSON.stringify({type:"audio",audio:b64(down(e.inputBuffer.getChannelData(0),audioContext.sampleRate))}))};microphone.connect(processor);processor.connect(audioContext.destination);started=true;startAt=Date.now();$("teacherSetup").style.display="none";$("teacherLive").style.display="block";timer=setInterval(()=>{const s=Math.floor((Date.now()-startAt)/1000);$("teacherTimer").textContent=String(Math.floor(s/60)).padStart(2,"0")+":"+String(s%60).padStart(2,"0")},1000);
}
$("startLectureBtn").onclick=()=>startWithVideoAndControls().catch(e=>err($("setupStatus"),e));
$("teacherMuteBtn").onclick=()=>{teacherMuted=!teacherMuted;stream?.getAudioTracks().forEach(t=>t.enabled=!teacherMuted);$("teacherMuteBtn").textContent=teacherMuted?"Unmute microphone":"Mute microphone"};
$("joinClassBtn").onclick=()=>{
  const code=$("classCode").value.trim().toUpperCase();
  const name=$("studentName").value.trim();
  if(!code){$("studentJoinStatus").textContent="Enter the class code shared by your teacher.";return}
  if(!name){$("studentJoinStatus").textContent="Enter your name.";return}
  $("joinClassBtn").disabled=true;
  $("studentJoinStatus").textContent="Connecting to the classroom...";
  studentSocket?.close();studentSocket=new WebSocket(`${wsBase}/ws/student`);
  studentPeer=makePeer(candidate=>studentSocket.send(JSON.stringify({type:"signal",signal:{kind:"candidate",candidate}})));
  studentPeer.ontrack=e=>{$("studentVideo").srcObject=e.streams[0]};
  studentSocket.onopen=()=>{studentSocket.send(JSON.stringify({type:"join",code,name,language:$("studentLang").value}));$("studentJoinStatus").textContent="Checking class code..."};
  studentSocket.onerror=()=>{ $("joinClassBtn").disabled=false; err($("studentJoinStatus"),Error("Cannot connect to the classroom server. Check the backend URL.")); };
  studentSocket.onclose=()=>{ if($("studentJoin").style.display!=="none") $("joinClassBtn").disabled=false; };
  studentSocket.onmessage=async e=>{const m=JSON.parse(e.data);if(m.type==="ready"){studentSocket.send(JSON.stringify({type:"student_ready"}));$("studentClassLabel").textContent=`Class ${code}`;$("studentJoinStatus").textContent="Connected — waiting for teacher";$("studentJoin").style.display="none";$("studentLive").style.display="block"}if(m.type==="signal"&&m.signal?.kind==="offer"){await studentPeer.setRemoteDescription(m.signal.description);for(const candidate of studentIceQueue)await studentPeer.addIceCandidate(candidate);studentIceQueue=[];const answer=await studentPeer.createAnswer();await studentPeer.setLocalDescription(answer);studentSocket.send(JSON.stringify({type:"signal",signal:{kind:"answer",description:studentPeer.localDescription}}))}if(m.type==="signal"&&m.signal?.kind==="candidate"){if(studentPeer.remoteDescription)await studentPeer.addIceCandidate(m.signal.candidate);else studentIceQueue.push(m.signal.candidate)}if(m.type==="class_ended"){studentPeer?.close();studentSocket.close();$("studentJoin").style.display="block";$("studentLive").style.display="none";$("studentJoinStatus").textContent="The teacher ended this class. Join an active class to continue.";$("studentJoinStatus").className="status error";$("joinClassBtn").disabled=false}if(m.type==="speak_accepted"){speakingAllowed=true;$("studentSpeakStatus").textContent="Teacher accepted. Speak in your selected language.";startStudentSpeech()}if(m.type==="speak_revoked"){speakingAllowed=false;$("studentSpeakStatus").textContent="Teacher stopped your speaking access."}if(m.type==="subtitle"){ $("studentCurrentLine").textContent=m.translated;const h=document.createElement("div");h.textContent=m.translated;h.className=$("studentLang").value==="te"?"te":"hi";$("studentHistory").appendChild(h);const bytes=Uint8Array.from(atob(m.audio_base64),c=>c.charCodeAt(0));currentAudio=new Audio(URL.createObjectURL(new Blob([bytes],{type:"audio/wav"})));currentAudio.muted=studentMuted;await currentAudio.play()}if(m.type==="error"){ $("joinClassBtn").disabled=false; err($("studentJoinStatus"),Error(m.message)); }};
};
$("studentMuteBtn").onclick=()=>{studentMuted=!studentMuted;if(currentAudio)currentAudio.muted=studentMuted;$("studentMuteBtn").textContent=studentMuted?"Unmute audio":"Mute audio"};
$("speakRequestBtn").onclick=()=>{studentSocket?.send(JSON.stringify({type:"speak_request"}));$("studentSpeakStatus").textContent="Speak request sent to teacher."};
let studentRecorder,studentStream;
async function startStudentSpeech(){if(studentRecorder)return;studentStream=await navigator.mediaDevices.getUserMedia({audio:true});studentRecorder=new AudioContext();const source=studentRecorder.createMediaStreamSource(studentStream),node=studentRecorder.createScriptProcessor(4096,1,1);node.onaudioprocess=e=>{if(speakingAllowed&&studentSocket?.readyState===1)studentSocket.send(JSON.stringify({type:"student_audio",audio:b64(down(e.inputBuffer.getChannelData(0),studentRecorder.sampleRate))}))};source.connect(node);node.connect(studentRecorder.destination)}
