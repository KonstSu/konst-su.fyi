// Contact form: sends the message through Web3Forms (https://web3forms.com)
// without leaving the page. Without JavaScript the form still posts normally.
(function () {
  var form = document.getElementById("contact-form");
  if (!form) return;
  var status = document.getElementById("form-status");
  var button = form.querySelector("button[type=submit]");

  function show(text, kind) {
    status.textContent = text;
    status.className = "form-status" + (kind ? " " + kind : "");
  }

  form.addEventListener("submit", function (event) {
    event.preventDefault();

    if (!form.checkValidity()) {
      var firstInvalid = form.querySelector(":invalid");
      if (firstInvalid) firstInvalid.focus();
      show("Please fill in your name, a valid email, a message and tick the consent box.", "err");
      return;
    }

    var key = form.querySelector("input[name=access_key]").value;
    if (!key || key.indexOf("YOUR_") === 0) {
      show("The form isn’t connected yet. Please contact me on LinkedIn for now.", "err");
      return;
    }

    button.disabled = true;
    show("Sending…");

    fetch(form.action, {
      method: "POST",
      headers: { Accept: "application/json" },
      body: new FormData(form)
    })
      .then(function (response) {
        // Web3Forms usually answers with JSON, but sometimes with an HTML
        // "success" page; treat any OK response without JSON as success.
        var type = response.headers.get("content-type") || "";
        if (type.indexOf("application/json") !== -1) return response.json();
        return { success: response.ok };
      })
      .then(function (data) {
        if (data && data.success) {
          form.reset();
          show("Thank you, your message has been sent. I’ll reply within a couple of days.", "ok");
        } else {
          show("Something went wrong. Please try again in a few minutes or contact me on LinkedIn.", "err");
        }
      })
      .catch(function () {
        show("Something went wrong. Please try again in a few minutes or contact me on LinkedIn.", "err");
      })
      .finally(function () { button.disabled = false; });
  });
})();
