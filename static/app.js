// static/app.js

// Affiche la popup d'achat avec SweetAlert
function handleSubscription(duration) {
  Swal.fire({
    title: 'Enter your phone number',
    input: 'text',
    inputPlaceholder: 'e.g. 0712345678',
    confirmButtonText: 'Subscribe',
    showCancelButton: true
  }).then((result) => {
    if (result.isConfirmed && result.value) {
      let phone = result.value;

      axios.post('/subscribe', {
        phone: phone,
        duration: duration
      }).then(res => {
        if (res.data.success) {
          Swal.fire(
            'Success!',
            'Access granted. Your ID: ' + res.data.id,
            'success'
          )
        }
      }).catch(err => {
        Swal.fire('Error', 'Subscription failed', 'error')
      });
    }
  });
}

// Permet à un utilisateur de restaurer l'accès avec son ID
function sayAmen() {
  Swal.fire({
    title: 'Enter your subscription ID',
    input: 'text',
    inputPlaceholder: 'Paste your ID here',
    confirmButtonText: 'Reconnect',
    showCancelButton: true
  }).then((result) => {
    if (result.isConfirmed && result.value) {
      let id = result.value;

      axios.post('/resume', {
        id: id
      }).then(res => {
        if (res.data.success) {
          Swal.fire('Reconnected', res.data.message, 'success')
        } else {
          Swal.fire('Error', res.data.message, 'error')
        }
      }).catch(err => {
        Swal.fire('Error', 'Failed to reconnect', 'error')
      });
    }
  });
}
