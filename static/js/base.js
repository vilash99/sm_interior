// --- Simple Mobile Nav Toggle ---
$(function () {
  const $toggle = $('#nav-toggle');
  const $menu = $('#mobile-menu');

  if ($toggle.length && $menu.length) {
    $toggle.on('click', function () {
      $menu.toggleClass('hidden');
    });
  }
});


// --- Menu Dropdown ---
$(function () {
  // Setup for each user-menu separately
  $('.user-menu').each(function () {
    const $wrapper = $(this);
    const $btn = $wrapper.find('.user-menu-btn');
    const $menu = $wrapper.find('.user-menu-dropdown');

    // Toggle on click
    $btn.on('click', function (e) {
      e.stopPropagation();

      // (Optional) close all other menus
      $('.user-menu-dropdown').not($menu).addClass('hidden');

      $menu.toggleClass('hidden');
    });
  });

  // Close all menus when clicking outside
  $(document).on('click', function () {
    $('.user-menu-dropdown').addClass('hidden');
  });
});


// --- Auto Hide Toast ---
$(function () {
  const $toasts = $('.toast');

  $toasts.each(function () {
    const $toast = $(this);

    // Start fade-out at 4.5 seconds
    setTimeout(() => {
      $toast.css('opacity', '0');
    }, 4500);

    // Remove from DOM at 3 seconds
    setTimeout(() => {
      $toast.remove();
    }, 3000);
  });
});
