import { LitElement, customElement, CSSResult, css, TemplateResult, html } from "lit-element";

import "@granite-elements/granite-spinner";

@customElement("hacs-spinner")
export class HacsSpinner extends LitElement {

    protected render(): TemplateResult | void {
        return html`
            <script>
            console.log("reloading in 5 sec");
            function sleep(time) {
                return new Promise((resolve) => setTimeout(resolve, time));
            }

            sleep(5000).then(() => {
                location.reload()
            });
            </script>
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