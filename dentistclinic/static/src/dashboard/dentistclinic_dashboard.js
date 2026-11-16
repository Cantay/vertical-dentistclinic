/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState } from "@odoo/owl";

export class DentistClinicDashboard extends Component {
    static template = "dentistclinic.Dashboard";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({ data: null, loading: true, selectedCompanyId: null });

        onWillStart(async () => {
            await this._loadData();
        });
    }

    async _loadData() {
        this.state.loading = true;
        this.state.data = await this.orm.call(
            "dental.dashboard",
            "get_dashboard_data",
            [],
            { company_id: this.state.selectedCompanyId || false }
        );
        this.state.loading = false;
    }

    async onRefresh() {
        await this._loadData();
    }

    async onCompanyChange(ev) {
        const value = ev.target.value;
        this.state.selectedCompanyId = value ? parseInt(value, 10) : null;
        await this._loadData();
    }

    openAppointments() {
        this.action.doAction("dentistclinic.action_dental_appointment");
    }

    openTreatmentPlans() {
        this.action.doAction("dentistclinic.action_dental_treatment_plan");
    }

    openLabOrders() {
        this.action.doAction("dentistclinic.action_dental_lab_order");
    }
}

registry.category("actions").add("dentistclinic_dashboard", DentistClinicDashboard);
