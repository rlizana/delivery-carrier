# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Yannick Vaucher
#    Copyright 2013 Camptocamp SA
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from ..pdf_utils import assemble_pdf

from openerp.osv import orm, fields
from tools.translate import _


class DeliveryCarrierLabelGenerate(orm.TransientModel):

    _name = 'delivery.carrier.label.generate'

    def _get_dispatch_ids(self, cr, uid, context=None):
        if context is None:
            context = {}
        res = False
        if (context.get('active_model') == 'picking.dispatch'
                and context.get('active_ids')):
            res = context['active_ids']
        return res

    _columns = {
        'dispatch_ids': fields.many2many('picking.dispatch',
                                         string='Picking Dispatch'),
        'generate_new_labels': fields.boolean('Generate new labels'),
    }

    _defaults = {
        'dispatch_ids': _get_dispatch_ids,
        'generate_new_labels': False,
    }

    def action_generate_labels(self, cr, uid, ids, context=None):
        """
        Call the creation of the delivery carrier label
        of the missing labels and get the existing ones
        Then merge all of them in a single PDF

        """
        this = self.browse(cr, uid, ids, context=context)[0]
        if not this.dispatch_ids:
            raise orm.except_orm(_('Error'), _('No picking dispatch selected'))

        picking_out_obj = self.pool.get('stock.picking.out')
        attachment_obj = self.pool.get('ir.attachment')

        for dispatch in this.dispatch_ids:
            # flatten all picking in one list to keep the order in case
            # if pickings have been ordered to ease packaging
            if this.generate_new_labels:
                pickings = [(pick, False)
                            for pick in dispatch.related_picking_ids]
            else:
                pickings = [(pick, pick.get_pdf_label()[pick.id])
                            for pick in dispatch.related_picking_ids]
            # get picking ids for which we want to generate pdf label
            picking_ids = [pick.id for pick, pdf in pickings
                           if not pdf or this.generate_new_labels]
            # generate missing picking labels
            picking_out_obj.action_generate_carrier_label(cr, uid,
                                                          picking_ids,
                                                          #file_type='pdf',
                                                          context=context)
            # Get all pdf files adding the newly generated ones
            data_list = [pdf or pick.get_pdf_label()[pick.id]
                         for pick, pdf in pickings]
            pdf_list = [data.decode('base64') for data in data_list if data]

            pdf_file = assemble_pdf(pdf_list)
            data = {
                'name': dispatch.name,
                'res_id': dispatch.id,
                'res_model': 'picking.dispatch',
                'datas': pdf_file.encode('base64'),
            }
            attachment_obj.create(cr, uid, data, context=context)

        return {
            'type': 'ir.actions.act_window_close',
        }
