class Connector {
  constructor() {
    this.connector_type_el = document.getElementById("connector_type");
    this.addEvents();
    this.changeConnectorTypeFields();
  }

  addEvents() {
    this.connector_type_el.addEventListener('change', this.changeConnectorTypeFields.bind(this));
  }

  changeConnectorTypeFields() {
    let connector_type_id = this.connector_type_el.value;
    let xhr = new XMLHttpRequest();
    xhr.responseType = 'json';
    xhr.open('GET', `/api/connector/${connector_type_id}`);
    xhr.send();

    xhr.onload = function () {
      document.querySelectorAll('.form-group').forEach(
        function (el) {
          if (el.querySelector('input[name]')) {
            if (!xhr.response.fields.includes(el.querySelector('input[name]').name)) {
              el.style.display = 'none';
            } else {
              el.style.display = 'block';
            }
          }
        });
    }
    xhr.onerror = function () {
      document.querySelectorAll('.form-group').forEach(
        el => el.style.display = 'block'
      );
    }
  }
}

// Load for connector.html
if (document.querySelector('.form-group')) {
  let form = new Connector();
}