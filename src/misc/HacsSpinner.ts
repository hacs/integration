import { LitElement, customElement, CSSResult, css, TemplateResult, html } from "lit-element";

import "@granite-elements/granite-spinner";

@customElement("hacs-spinner")
export class HacsSpinner extends LitElement {

    protected render(): TemplateResult | void {
        return html`
            <granite-spinner
                color="var(--primary-color)"
                active hover
                size=400
                containerHeight=100%
                >
            </granite-spinner>
            `;
    }
}