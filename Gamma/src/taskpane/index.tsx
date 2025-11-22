import * as React from "react";
import { createRoot } from "react-dom/client";
import App from "./components/App";
import { FluentProvider, webLightTheme } from "@fluentui/react-components";

/* FIX: Definim titlul aici pentru a fi sigur ca exista.
*/

const rootElement = document.getElementById("container");
const root = createRoot(rootElement!);

/* PASUL 1: Randam aplicatia IMEDIAT cu statusul false. 
   Astfel utilizatorul vede macar un spinner, nu ecran alb.
*/
root.render(
  <FluentProvider theme={webLightTheme}>
    <App isOfficeInitialized={false} />
  </FluentProvider>
);

/* PASUL 2: Ascultam cand Excel e gata si re-randam cu true.
*/
Office.onReady(() => {
  root.render(
    <FluentProvider theme={webLightTheme}>
      <App isOfficeInitialized={true} />
    </FluentProvider>
  );
});

/* PASUL 3: Hot Module Replacement (pentru development rapid)
*/
if ((module as any).hot) {
  (module as any).hot.accept("./components/App", () => {
    const NextApp = require("./components/App").default;
    root.render(
      <FluentProvider theme={webLightTheme}>
        <NextApp isOfficeInitialized={true} />
      </FluentProvider>
    );
  });
}