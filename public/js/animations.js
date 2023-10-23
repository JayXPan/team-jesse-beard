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


var coll = document.getElementsByClassName("collapsible");
var i;

for (i = 0; i < coll.length; i++) {
  coll[i].addEventListener("click", function() {
    this.classList.toggle("active");
    var content = this.nextElementSibling;
    if (content.style.display === "block") {
      content.style.display = "none";
    } else {
      content.style.display = "block";
    }
  });
}
