/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState } from "@odoo/owl";
import { X2ManyField, x2ManyField } from "@web/views/fields/x2many/x2many_field";

const UPPER_RIGHT = [18, 17, 16, 15, 14, 13, 12, 11];
const UPPER_LEFT = [21, 22, 23, 24, 25, 26, 27, 28];
const LOWER_LEFT = [31, 32, 33, 34, 35, 36, 37, 38];
const LOWER_RIGHT = [48, 47, 46, 45, 44, 43, 42, 41];

export class OdontogramField extends Component {
    static template = "dentistclinic.OdontogramField";
    static props = { ...X2ManyField.props };
    static components = { X2ManyField };

    setup() {
        this.state = useState({ selectedTooth: null });
        this.quadrants = {
            upperRight: UPPER_RIGHT,
            upperLeft: UPPER_LEFT,
            lowerLeft: LOWER_LEFT,
            lowerRight: LOWER_RIGHT,
        };
    }

    get lines() {
        return this.props.record.data[this.props.name].records;
    }

    getToothLines(toothNumber) {
        const toothStr = String(toothNumber);
        return this.lines.filter((line) => line.data.tooth_number === toothStr);
    }

    getToothClass(toothNumber) {
        const toothLines = this.getToothLines(toothNumber);
        if (!toothLines.length) {
            return "dental-tooth";
        }
        if (toothLines.some((line) => line.data.state === "done")) {
            return "dental-tooth dental-tooth-done";
        }
        if (toothLines.some((line) => line.data.state === "invoiced")) {
            return "dental-tooth dental-tooth-invoiced";
        }
        return "dental-tooth dental-tooth-planned";
    }

    onToothClick(toothNumber) {
        this.state.selectedTooth = toothNumber;
    }

    async addLineForSelectedTooth() {
        if (!this.state.selectedTooth) {
            return;
        }
        const list = this.props.record.data[this.props.name];
        const newRecord = await list.addNewRecord({ position: "bottom" });
        await newRecord.update({ tooth_number: String(this.state.selectedTooth) });
    }
}

export const odontogramField = {
    ...x2ManyField,
    component: OdontogramField,
};

registry.category("fields").add("dental_odontogram", odontogramField);
