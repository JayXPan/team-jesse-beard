"use strict";

/*Fade Animation referenced from potatoDie.nl - "Animation on Page Load"*/
document.documentElement.classList.add('loadin');
window.onload = function(){
	document.documentElement.classList.remove('loadin');
};

window.addEventListener("load", function(){
document.getElementById("mainTitle").addEventListener("click", gamerTime);
});

function gamerTime(){
	document.documentElement.classList.add('gamer');
	/*setTimeout referenced from SitePoint - "Delay, Sleep, Pause & Wait in Javascript"*/
	setTimeout(()=>{document.documentElement.classList.remove('gamer');}, 3000);
}