from django.conf.urls.defaults import url, patterns
from django.views.decorators.csrf import csrf_exempt

from shop.views.checkout import (
    # SelectPaymentView,
    # SelectShippingView,
    CheckoutSelectionView,
    PaymentBackendRedirectView,
    ShippingBackendRedirectView,
    ThankYouView,
)

urlpatterns = patterns('',
    url(r'^checkout/$', CheckoutSelectionView.as_view(),
        name='checkout_selection'  # First step of the checkout process
        ),
    #url(r'^checkout/ship/$', SelectShippingView.as_view(),
    #    name='checkout_shipping'  # First step of the checkout process
    #    ),
    url(r'^checkout/ship/$', ShippingBackendRedirectView.as_view(),
        name='checkout_shipping'  # First step of the checkout process
        ),
    #url(r'^checkout/pay/$', SelectPaymentView.as_view(),
    #    name='checkout_payment'  # Second step of the checkout process
    #    ),
    url(r'^checkout/pay/$', PaymentBackendRedirectView.as_view(),
        name='checkout_payment'  # First step of the checkout process
        ),
    url(r'^checkout/thank_you/$', csrf_exempt(ThankYouView.as_view()),
        name='thank_you_for_your_order'  # Second step of the checkout process
        ),
    )
