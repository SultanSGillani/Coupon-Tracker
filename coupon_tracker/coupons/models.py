from django.db import models
from django.utils import timezone
from django.conf import settings
from django.dispatch import Signal

user = settings.AUTH_USER_MODEL

COUPON_TYPES = (
	('monetary', 'Money based coupon'),
	('percentage', 'Percentage discount'),
	('virtual_currency', 'Virtual currency'),
)

redeem_done = Signal(providing_args=["coupon"])


class CouponManager(models.Manager):
	def create_coupon(self, type, value, user=None, valid_until=None):
		coupon = self.create(
			value=value,
			user=user,
			type=type,
			valid_until=valid_until,
		)
		coupon = Coupon.objects.create(type, value, user, valid_until)
		if not isinstance(user, list):
			Coupon(user=user, coupon=coupon).save()
		return coupon

	def create_coupons(self, quantity, type, value, valid_until=None):
		coupons = []
		for i in range(quantity):
			coupons.append(self.create_coupon(type, value, valid_until))
		return coupons

	def used(self):
		return self.exclude(users__redeemed_at__isnull=True)

	def unused(self):
		return self.filter(users__redeemed_at__isnull=True)

	def expired(self):
		return self.filter(valid_until__lt=timezone.now())


# Create your models here.
class Coupon(models.Model):
	coupon = models.ForeignKey('self', on_delete=models.CASCADE)
	price = models.DecimalField(max_digits=8, decimal_places=2)
	discount = models.DecimalField(max_digits=6, decimal_places=2)
	store = models.CharField(max_length=200)
	created_at = models.DateTimeField(auto_now_add=True)
	type = models.CharField(max_length=20, choices=COUPON_TYPES)
	valid_until = models.DateTimeField(blank=True, null=True)
	user = models.ForeignKey(user, null=True, blank=True, on_delete=models.SET_NULL)
	redeemed_at = models.DateTimeField(blank=True, null=True)
	objects = CouponManager()

	def __str__(self):
		return str(self.user)

	class Meta:
		ordering = ['created_at']

	def expired(self):
		return self.valid_until is not None and self.valid_until < timezone.now()

	@property
	def redeemed_at(self):
		try:
			return user.filter(redeemed_at__isnull=False).order_by('redeemed_at').last().redeemed_at
		except user.through.DoesNotExist:
			return None

	def redeem(self, user=None):
		coupon_user = user.get(user=user)
		coupon_user.redeemed_at = timezone.now()
		coupon_user.save()
		redeem_done.send(sender=self.__class__, coupon=self)
