// Collapsible
var coll = document.getElementsByClassName("collapsible");
const startmessage = "Hello! This is the chatbot of BoeingLearning. How can I help you today &#x1F603;?";

for (let i = 0; i < coll.length; i++) {
    coll[i].addEventListener("click", function () {
        this.classList.toggle("active");

        var content = this.nextElementSibling;

        if (content.style.maxHeight) {
            content.style.maxHeight = null;
        } else {
            content.style.maxHeight = content.scrollHeight + "px";
        }

    });
}

// function getTime() {
//     let today = new Date();
//     hours = today.getHours();
//     minutes = today.getMinutes();

//     if (hours < 10) {
//         hours = "0" + hours;
//     }

//     if (minutes < 10) {
//         minutes = "0" + minutes;
//     }

//     let time = hours + ":" + minutes;
//     return time;
// }

// Gets the first message
function firstBotMessage() {
    let firstMessage = startmessage
    document.getElementById("botStarterMessage").innerHTML = '<p class="botText"><span>' + firstMessage + '</span></p>';

    let time = getTime();

    $("#chat-timestamp").append(time);
    document.getElementById("userInput").scrollIntoView(false);
}

firstBotMessage();

//Gets the text text from the input box and processes it
function getResponse() {

    let userText = $("#textInput").val();

    let response;
    if (userText === "") {
        response = startmessage
        displayChatResponse(response);
        return;
    }

    let userHtml = '<p class="userText"><span>' + userText + '</span></p>';

    $("#textInput").val("");
    $("#chatbox").append(userHtml);
    document.getElementById("chat-bar-bottom").scrollIntoView(true);

    showTypingIndicator();

    setTimeout(() => {
        sendChatMessage(userText);
    }, 5000)

}

// send an AJAX request to the Django back-end with the user's input
function sendChatMessage(input) {
  fetch('/chatbot/api/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCookie('csrftoken'),
    },
    body: JSON.stringify({ input: input }),
  })
    .then((response) => response.json())
    .then((data) => {
        hideTypingIndicator();
        displayChatResponse(data.response);
    });
}

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// A custom function to handle displaying the chatbot's response
function displayChatResponse(response) {
    let botHtml = '<p class="botText"><span>' + response + '</span></p>';
    $("#chatbox").append(botHtml);

    document.getElementById("chat-bar-bottom").scrollIntoView(true);
}


// Handles sending text via button clicks
function buttonSendText(sampleText) {
    let userHtml = '<p class="userText"><span>' + sampleText + '</span></p>';

    $("#textInput").val("");
    $("#chatbox").append(userHtml);
    document.getElementById("chat-bar-bottom").scrollIntoView(true);

    //Uncomment this if you want the bot to respond to this buttonSendText event
    // setTimeout(() => {
    //     getHardResponse(sampleText);
    // }, 1000)
}

function sendButton() {
    getResponse();
}

function heartButton() {
    buttonSendText("Heart clicked!")
}

// Press enter to send a message
$("#textInput").keypress(function (e) {
    if (e.which == 13) {
        getResponse();
    }
});

// typing animation
function showTypingIndicator() {
    // Create the main container div
const typingContainer = document.createElement('div');
typingContainer.classList.add('messages__item--typing');

// Create the three span elements with the 'messages__dot' class
for (let i = 0; i < 3; i++) {
  const dot = document.createElement('span');
  dot.classList.add('messages__dot');
  typingContainer.appendChild(dot);
}

// Append the typingContainer to the desired parent element

$("#chatbox").append(typingContainer);
document.getElementById("chat-bar-bottom").scrollIntoView(true);
}

function hideTypingIndicator() {
const typingContainer = document.querySelector('.messages__item--typing');
typingContainer.remove();

}