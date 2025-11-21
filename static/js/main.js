// Animación del botón principal con GSAP
document.addEventListener("DOMContentLoaded", function () {
    // Confirmar acciones de botones (admin citas)
    const confirmButtons = document.querySelectorAll(".btn-confirm");
    confirmButtons.forEach(btn => {
        btn.addEventListener("click", function (e) {
            e.preventDefault();
            const url = this.href;
            const msg = this.dataset.message || "¿Estás seguro?";

            Swal.fire({
                title: msg,
                icon: "warning",
                showCancelButton: true,
                confirmButtonText: "Sí",
                cancelButtonText: "No",
                confirmButtonColor: "#28a745",
                cancelButtonColor: "#6c757d"
            }).then(result => {
                if (result.isConfirmed) {
                    window.location.href = url;
                }
            });
        });
    });

    // Confirmar reserva de cita
    const bookingForm = document.getElementById("booking-form");
    if (bookingForm) {
        bookingForm.addEventListener("submit", function (e) {
            e.preventDefault();
            Swal.fire({
                title: "¿Confirmar tu cita?",
                text: "Revisa que la fecha y hora sean correctas.",
                icon: "question",
                showCancelButton: true,
                confirmButtonText: "Confirmar",
                cancelButtonText: "Volver",
                confirmButtonColor: "#f0d45e",
                cancelButtonColor: "#6c757d"
            }).then(result => {
                if (result.isConfirmed) {
                    bookingForm.submit();
                }
            });
        });
    }

    // Confirmar cierre de sesión
    const logoutLink = document.getElementById("logout-link");
    if (logoutLink) {
        logoutLink.addEventListener("click", function (e) {
            e.preventDefault();
            const url = this.href;

            Swal.fire({
                title: "¿Cerrar sesión?",
                icon: "question",
                showCancelButton: true,
                confirmButtonText: "Sí, salir",
                cancelButtonText: "Cancelar",
                confirmButtonColor: "#d33",
                cancelButtonColor: "#6c757d"
            }).then(result => {
                if (result.isConfirmed) {
                    window.location.href = url;
                }
            });
        });
    }
});

