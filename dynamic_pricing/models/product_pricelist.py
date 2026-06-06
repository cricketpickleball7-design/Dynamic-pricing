from odoo import fields, models


class ProductPricelist(models.Model):
    _inherit = "product.pricelist"

    def _compute_price_rule(
        self,
        products,
        quantity,
        *,
        currency=None,
        uom=None,
        date=False,
        compute_price=True,
        **kwargs,
    ):
        results = super()._compute_price_rule(
            products,
            quantity,
            currency=currency,
            uom=uom,
            date=date,
            compute_price=compute_price,
            **kwargs,
        )
        if not compute_price or self.env.context.get("skip_dynamic_pricing") or not products:
            return results

        currency = currency or self.currency_id or self.env.company.currency_id
        conversion_date = date or fields.Date.context_today(self)
        for product in products:
            template = (
                product
                if product._name == "product.template"
                else product.product_tmpl_id
            )
            if not template.dynamic_pricing_enabled:
                continue

            dynamic_price = template._get_dynamic_pricing_price(
                product=product,
                currency=currency,
                uom=uom,
                date=conversion_date,
            )
            if dynamic_price is False:
                continue

            results[product.id] = (dynamic_price, False)
        return results

