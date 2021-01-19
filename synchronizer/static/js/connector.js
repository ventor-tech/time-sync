$(function () {
  class Connector {
    constructor() {
      this.addEvents();
    }

    addEvents() {
        for (let el of document.querySelectorAll('.form-group')) {
          if (el.children[1].id == 'connector_type') {
            el.addEventListener('click', this.callConnectorFormFields.bind(this));
          } else {
            el.hidden = true;
          }
        }
    }

    callConnectorFormFields(el) {
          $.get({
              url: `/connector/api/delete/`,
              type: 'GET'
          }).then(
              function () {
                  recordEl.closest('.inline-field').remove();
              },
              function (xhr) {
                  if (xhr.responseJSON && xhr.responseJSON.error) {
                      alert(xhr.responseJSON.error)
                  } else {
                      alert(`Error ${xhr.status}: ${xhr.statusText}`);
                  }
              })
            }
  }



// Load for connector.html
if (document.querySelector('.form-group')) {
    let form = new Connector();
  }
});