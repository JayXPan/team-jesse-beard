showClock();
setInterval(showClock, 1000);

"use strict";
function showClock(){
   
   //thisDay set to the current time
   var thisDay = new Date();
   let localDate = thisDay.toLocaleDateString();
   let localTime = thisDay.toLocaleTimeString();

   //Setting the time and date at the top of the page to the current time
   document.getElementById("currentTime").innerHTML = localDate + "<br>" + localTime;
}