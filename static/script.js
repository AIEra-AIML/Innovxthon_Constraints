/* =========================================================
   INNOVXTHON — EXACT UI + 4 ROUND TEAM ASSIGNMENT
========================================================= */
const challenges = {
    1:{number:"01",title:"SPEAK IT",subtitle:"VOICE INTERACTION",description:"At least one important action must be performed using voice input."},
    2:{number:"02",title:"LIVE WIRE",subtitle:"REAL-TIME RESPONSE",description:"Your solution must provide a real-time response, update or action."},
    3:{number:"03",title:"SHOW YOUR WHY",subtitle:"EXPLAINABLE OUTPUT",description:"Your solution must explain the reason behind at least one important result."},
    4:{number:"04",title:"MAKE IT YOURS",subtitle:"PERSONALIZATION",description:"Let the user customize at least one important feature of your solution."},
    5:{number:"05",title:"BREAK THE INPUT",subtitle:"ALTERNATIVE INTERACTION",description:"Support at least two different ways of interacting with your solution."}
};

const experience=document.getElementById("experience");
const animationLayer=document.getElementById("animation-layer");
const fullscreen=document.getElementById("fullscreen-challenge");
const fullNumber=document.getElementById("full-number");
const fullTitle=document.getElementById("full-title");
const fullSubtitle=document.getElementById("full-subtitle");
const fullDescription=document.getElementById("full-description");
const backButton=document.getElementById("back-button");
const cards=[...document.querySelectorAll(".challenge-card")];
const gate=document.getElementById("team-gate");
const form=document.getElementById("team-form");
const teamInput=document.getElementById("team-number");
const gateError=document.getElementById("gate-error");
const statusBar=document.getElementById("team-status-bar");
const currentTeamEl=document.getElementById("current-team");
const currentRoundEl=document.getElementById("current-round");
const doneScreen=document.getElementById("done-screen");

let isAnimating=false;
let isSaving=false;
let activeCard=null;
let teamNo=null;
let state=null;
let pollingTimer=null;

function wait(ms){return new Promise(resolve=>setTimeout(resolve,ms));}

function createFlyingCard(originalCard){
    const rect=originalCard.getBoundingClientRect();
    const width=rect.width,height=rect.height;
    const originalCenterX=rect.left+(width/2),originalCenterY=rect.top+(height/2);
    const viewportCenterX=window.innerWidth/2,viewportCenterY=window.innerHeight/2;
    const fromX=originalCenterX-viewportCenterX,fromY=originalCenterY-viewportCenterY;
    const flying=originalCard.cloneNode(true);
    flying.classList.remove("used","locked");
    flying.classList.add("flying-card");
    flying.style.setProperty("--card-width",`${width}px`);
    flying.style.setProperty("--card-height",`${height}px`);
    flying.style.setProperty("--from-x",`${fromX}px`);
    flying.style.setProperty("--from-y",`${fromY}px`);
    flying.style.setProperty("--start-rotate",Math.random()>0.5?"2.5deg":"-2.5deg");
    animationLayer.appendChild(flying);
    return flying;
}

function showFullscreen(id){
    const challenge=challenges[id]; if(!challenge)return;
    fullNumber.textContent=challenge.number;
    fullTitle.textContent=challenge.title;
    fullSubtitle.textContent=challenge.subtitle;
    fullDescription.textContent=challenge.description;
    fullscreen.classList.add("active");
}
function hideFullscreen(){fullscreen.classList.remove("active");}

async function animateReveal(card){
    if(isAnimating)return;
    isAnimating=true; activeCard=card;
    const id=Number(card.dataset.id);
    const flying=createFlyingCard(card);
    card.classList.add("is-hidden");
    await wait(80); flying.classList.add("move-center");
    await wait(1150); flying.classList.add("glow");
    await wait(750); flying.classList.add("flip");
    await wait(1050);
    await wait(700);
    showFullscreen(id);
    await wait(750);
    flying.remove();
    card.classList.remove("is-hidden");
    isAnimating=false;
}

async function selectChallenge(card){
    if(isAnimating || isSaving || !teamNo || !state)return;
    const id=Number(card.dataset.id);
    if(state.done)return;
    if(state.current_selection){
        if(Number(state.current_selection.challenge_id)===id) animateReveal(card);
        return;
    }
    if(state.selected.includes(id))return;
    if(!state.can_select)return;
    isSaving=true;
    try{
        const res=await fetch("/api/select",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({team_no:teamNo,challenge_id:id})});
        const data=await res.json();
        if(!res.ok){alert(data.message||"Selection failed.");isSaving=false;return;}
        state=data.state;
        applyState();
        isSaving=false;
        await animateReveal(card);
    }catch(e){console.error(e);alert("Unable to save selection. Please check the server.");isSaving=false;}
}

cards.forEach(card=>card.addEventListener("click",()=>selectChallenge(card)));

backButton.addEventListener("click",()=>{
    hideFullscreen();
    if(activeCard)setTimeout(()=>activeCard.scrollIntoView({behavior:"smooth",block:"center"}),400);
});
document.addEventListener("keydown",event=>{
    if(event.key==="Escape"&&fullscreen.classList.contains("active"))hideFullscreen();
});
document.addEventListener("keydown",event=>{
    if(isAnimating||fullscreen.classList.contains("active")||!teamNo)return;
    const number=Number(event.key);
    if(number>=1&&number<=5){
        const card=cards.find(item=>Number(item.dataset.id)===number);
        if(card){card.scrollIntoView({behavior:"smooth",block:"center"});setTimeout(()=>selectChallenge(card),650);}
    }
});
cards.forEach(card=>card.addEventListener("pointerdown",event=>{if(event.pointerType==="touch")event.preventDefault();}));

function applyState(){
    if(!state)return;
    currentTeamEl.textContent=`INX ${String(teamNo).padStart(2,"0")}`;
    if(state.done){
        currentRoundEl.textContent="DONE";
        cards.forEach(c=>{c.classList.remove("locked","is-hidden"); if(state.selected.includes(Number(c.dataset.id)))c.classList.add("used");});
        doneScreen.classList.add("active");
        return;
    }
    doneScreen.classList.remove("active");
    currentRoundEl.textContent=`${state.round} / 4`;
    cards.forEach(card=>{
        const id=Number(card.dataset.id);
        const selectedBefore=state.selected.includes(id);
        const currentSelected=state.current_selection && Number(state.current_selection.challenge_id)===id;
        card.classList.remove("locked","used","is-hidden");
        if(selectedBefore || currentSelected)card.classList.add("used");
        if(state.current_selection){
            if(!currentSelected)card.classList.add("locked");
        }else if(selectedBefore){
            card.classList.add("locked");
        }
    });
    statusBar.classList.add("visible");
}

async function loadState(){
    if(!teamNo)return;
    try{
        const res=await fetch(`/api/team/${teamNo}`);
        if(!res.ok)return;
        state=await res.json();
        applyState();
    }catch(e){console.error(e);}
}

async function enterTeam(raw){
    const value=String(raw||"").trim().replace(/^INX\s*/i,"");
    if(!/^([1-9]|[1-3][0-9]|40)$/.test(value)){
        gateError.textContent="ENTER A TEAM NUMBER FROM 01 TO 40."; return;
    }
    const number=Number(value);
    try{
        const res=await fetch("/api/enter-team",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({team_no:number})});
        const data=await res.json();
        if(!res.ok){gateError.textContent=data.message||"Unable to enter team.";return;}
        teamNo=number; state=data.state;
        gate.classList.add("hidden");
        experience.style.display="block";
        applyState();
        startPolling();
    }catch(e){gateError.textContent="SERVER ERROR. PLEASE TRY AGAIN.";console.error(e);}
}

form.addEventListener("submit",e=>{e.preventDefault();enterTeam(teamInput.value);});
const changeTeamButton=document.getElementById("change-team-button");
if(changeTeamButton){
    changeTeamButton.addEventListener("click",()=>{
        teamNo=null; state=null;
        doneScreen.classList.remove("active");
        statusBar.classList.remove("visible");
        gate.classList.remove("hidden");
        experience.style.display="none";
        teamInput.value="";
        teamInput.focus();
    });
}
teamInput.addEventListener("input",()=>{teamInput.value=teamInput.value.replace(/\D/g,"").slice(0,2);});

function startPolling(){
    if(pollingTimer)clearInterval(pollingTimer);
    pollingTimer=setInterval(async()=>{
        if(!teamNo||isAnimating)return;
        await loadState();
    },1200);
}

(function init(){
    experience.style.display="none";
    teamInput.focus();
})();
