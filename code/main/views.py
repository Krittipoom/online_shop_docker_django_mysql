from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from products.models import *
from order_manager.models import *
from math import floor
from django.conf import settings
from django.views.generic import View

from .get_first_request.get_all_computer_data import GetAllComputerData
from .get_first_request.get_all_smartphone_data import GetAllSmartphoneData
from .get_first_request.get_all_headphone_data import GetAllHeadphoneData
from .get_first_request.get_all_cloth_data import GetAllClothData

from .form.paymethod import CheckoutForm

import stripe
#stripe.api_key = settings.STRIPE_SECRET_KEY

# Create your views here.
def home(request):

	if 'computer_data' not in request.session:
		request.session['computer_data'] = GetAllComputerData()

	if 'smartphone_data' not in request.session:
		request.session['smartphone_data'] = GetAllSmartphoneData()

	if 'headphone_data' not in request.session:
		request.session['headphone_data'] = GetAllHeadphoneData()

	if 'cloth_data' not in request.session:
		request.session['cloth_data'] = GetAllClothData()

	return render(request, "homepage.html")

def product_computer(request, id):
	product = Computer.objects.get(id=id)
	fullstar = "★" * floor(product.stars)
	return render(request, "store/product/computer.html", {'data': product, 'fullstar': fullstar})

def product_smartphone(request, id):
	product = Smartphone.objects.get(id=id)
	fullstar = "★" * floor(product.stars)
	return render(request, "store/product/smartphone.html", {'data': product, 'fullstar': fullstar})

def product_headphone(request, id):
	product = Headphone.objects.get(id=id)
	fullstar = "★" * floor(product.stars)
	return render(request, "store/product/headphone.html", {'data': product, 'fullstar': fullstar})

def product_cloth(request, id):
	product = Cloth.objects.get(id=id)
	fullstar = "★" * floor(product.stars)
	return render(request, "store/product/cloth.html", {'data': product, 'fullstar': fullstar})

@login_required
def OrderSummaryView(request):
	try:
		order = Order.objects.get(user=request.user, ordered=False)
		quantity = order.items.values_list('quantity', flat=True)
		prod_id_list = order.items.values_list('prod_item_id', flat=True)
		prod_list = []
		for i in range(len(prod_id_list)):
			prod = ProductItem.objects.get(id=prod_id_list[i])
			if 'unisex' in prod.title or 'Unisex' in prod.title or 'Female' in prod.title or 'Male' in prod.title:
				prodlink = "/cloth/product/"+str(Cloth.objects.get(title=prod.title).id)
			elif 'Desktop' in prod.title or 'Laptop' in prod.title:
				prodlink = "/computer/product/"+str(Computer.objects.get(title=prod.title).id)
			elif 'Headphone' in prod.title or 'Headset' in prod.title or 'Earphone' in prod.title:
				prodlink = "/headphone/product/"+str(Headphone.objects.get(title=prod.title).id)
			else:
				prodlink = "/smartphone/product/"+str(Smartphone.objects.get(title=prod.title).id)

			prod_list.append({'title': prod.title, 'prodlink': prodlink, 'image': prod.image, 'price': prod.price, 'totalprice': prod.price*quantity[i], 'quantity': quantity[i]})
		
		total_item = sum([prod['quantity'] for prod in prod_list])
		total_and_delivery_price = sum([prod['totalprice'] for prod in prod_list]) + 50

	except ObjectDoesNotExist:
		messages.error(request, "You don't have an active order")
		return redirect(request.META.get('HTTP_REFERER'))

	return render(request, 'store/order_summary.html', {'prodlist': prod_list, 'total_item': total_item, 'total_and_delivery_price': total_and_delivery_price})

@login_required
def add_to_cart(request, title):
	prod_item = get_object_or_404(ProductItem, title=title)    
	order_qs = Order.objects.filter(user=request.user, ordered=False)
	
	if order_qs.exists():
		order = order_qs[0]
		
		if order.items.filter(prod_item=prod_item, ordered=False).exists():
			order_item, created = order.items.get_or_create(prod_item=prod_item, ordered=False)
			order_item.quantity += 1
			order_item.save()
			messages.info(request, "This item quality from your cart was updated.")
			return redirect(request.META.get('HTTP_REFERER'))
		else:
			order_item = OrderProductItem.objects.create(prod_item=prod_item, user=request.user, ordered=False)
			order.items.add(order_item)
			messages.info(request, "This item was added to your cart.")
			return redirect(request.META.get('HTTP_REFERER'))
	else:
		ordered_date = timezone.now()
		order = Order.objects.create(user=request.user, ordered_date=ordered_date)
		order_item = OrderProductItem.objects.create(prod_item=prod_item, user=request.user, ordered=False)
		order.items.add(order_item)
		messages.info(request, "This item was added to from your cart.")
		return redirect(request.META.get('HTTP_REFERER'))

@login_required
def remove_from_cart(request, title):
	prod_item = get_object_or_404(ProductItem, title=title)
	order_qs = Order.objects.filter(user=request.user, ordered=False)

	if order_qs.exists():
		order = order_qs[0]

		if order.items.filter(prod_item__title=prod_item.title).exists():
			order_item = OrderProductItem.objects.filter(prod_item=prod_item, user=request.user, ordered=False)[0]
			order.items.remove(order_item)
			order_item.delete()
			messages.info(request, "This item was removed from your cart.")
			return redirect(request.META.get('HTTP_REFERER'))
		else:
			messages.info(request, "This item was not in your cart")
			return redirect(request.META.get('HTTP_REFERER'))
	else:
		messages.info(request, "You do not have an active order")
		return redirect(request.META.get('HTTP_REFERER'))


@login_required
def remove_single_item_from_cart(request, title):
	prod_item = get_object_or_404(ProductItem, title=title)
	order_qs = Order.objects.filter(user=request.user, ordered=False)

	if order_qs.exists():
		order = order_qs[0]

		if order.items.filter(prod_item__title=prod_item.title).exists():
			order_item = OrderProductItem.objects.filter(prod_item=prod_item, user=request.user, ordered=False)[0]
			if order_item.quantity > 1:
				order_item.quantity -= 1
				order_item.save()
				messages.info(request, "This item quantity was updated.")
				return redirect(request.META.get('HTTP_REFERER'))
			else:
				order.items.remove(order_item)
				messages.info(request, "This item quantity was updated.")
				return redirect(request.META.get('HTTP_REFERER'))
		else:
			messages.info(request, "This item was not in your cart")
			return redirect(request.META.get('HTTP_REFERER'))
	else:
		messages.info(request, "You do not have an active order")
		return redirect(request.META.get('HTTP_REFERER'))

def is_valid_form(values):
	valid = True
	for field in values:
		if field == '':
			valid = False
	return valid

class CheckoutView(View):
	def get(self, *args, **kwargs):
		try:
			order = Order.objects.get(user=self.request.user, ordered=False)
			form = CheckoutForm()
			context = {
				'form': form,
				'order': order,
			}

			shipping_address_qs = Address.objects.filter(
				user=self.request.user,
				address_type='S',
				default=True
			)
			if shipping_address_qs.exists():
				context.update(
					{'default_shipping_address': shipping_address_qs[0]})

			billing_address_qs = Address.objects.filter(
				user=self.request.user,
				address_type='B',
				default=True
			)
			if billing_address_qs.exists():
				context.update(
					{'default_billing_address': billing_address_qs[0]})
			return render(self.request, "store/checkout.html", context)
		except ObjectDoesNotExist:
			messages.info(self.request, "You do not have an active order")
			return redirect("checkout")

	def post(self, *args, **kwargs):
		form = CheckoutForm(self.request.POST or None)
		try:
			order = Order.objects.get(user=self.request.user, ordered=False)
			if form.is_valid():

				use_default_shipping = form.cleaned_data.get(
					'use_default_shipping')
				if use_default_shipping:
					address_qs = Address.objects.filter(
						user=self.request.user,
						address_type='S',
						default=True
					)
					if address_qs.exists():
						shipping_address = address_qs[0]
						order.shipping_address = shipping_address
						order.save()
					else:
						messages.info(
							self.request, "No default shipping address available")
						return redirect('checkout')
				else:
					shipping_address1 = form.cleaned_data.get(
						'shipping_address')
					shipping_address2 = form.cleaned_data.get(
						'shipping_address2')
					shipping_country = form.cleaned_data.get(
						'shipping_country')
					shipping_zip = form.cleaned_data.get('shipping_zip')

					if is_valid_form([shipping_address1, shipping_country, shipping_zip]):
						shipping_address = Address(
							user=self.request.user,
							street_address=shipping_address1,
							apartment_address=shipping_address2,
							zip=shipping_zip,
							address_type='S'
						)
						shipping_address.save()

						order.shipping_address = shipping_address
						order.save()

						set_default_shipping = form.cleaned_data.get(
							'set_default_shipping')
						if set_default_shipping:
							shipping_address.default = True
							shipping_address.save()

					else:
						messages.info(
							self.request, "Please fill in the required shipping address fields")
						return redirect("checkout")

				payment_option = form.cleaned_data.get('payment_option')

				if payment_option == 'S':
					return redirect('payment')
				else: # payment_option == 'P':
					return redirect('payment')

		except ObjectDoesNotExist:
			messages.warning(self.request, "You do not have an active order")
			return redirect("ordersummary")

def TestPayment(request):

	return render(request, "store/payment.html")

@login_required
def ClearOrder(request):
	try:
		order = Order.objects.get(user=request.user)
		order.ordered = True
		order.save(update_fields=["ordered"])
		messages.info(request, "Thank you for testing my website!, Order successful")

	except:
		messages.error(request, "Order not successful!")
		return redirect(request.META.get('HTTP_REFERER'))

	return render(request, 'store/order_summary.html')
