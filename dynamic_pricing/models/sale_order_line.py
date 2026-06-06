from odoo import models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def _get_display_price_ignore_combo(self):
        self.ensure_one()
        if self.product_id.product_tmpl_id.dynamic_pricing_enabled:
            return self._get_pricelist_price()
        return super()._get_display_price_ignore_combo()

    def _get_pricelist_price(self):
        self.ensure_one()
        if not self.product_id.product_tmpl_id.dynamic_pricing_enabled:
            return super()._get_pricelist_price()

        return self.order_id.pricelist_id._get_product_price(
            product=self.product_id.with_context(**self._get_product_price_context()),
            **self._get_pricelist_kwargs(),
        )

