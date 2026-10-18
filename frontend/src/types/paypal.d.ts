// Minimum shape needed for the PayPal Smart Buttons SDK
// (https://www.paypal.com/sdk/js). The actual library is loaded via a runtime script.

export {};

declare global {
  interface Window {
    paypal?: {
      Buttons: (config: PayPalButtonsConfig) => PayPalButtonsInstance;
    };
  }

  interface PayPalButtonsConfig {
    /** Called when the buyer clicks the button. Resolve with a valid PayPal order id. */
    createOrder?(): Promise<string> | string;
    /** Called after the buyer approves. Resolve when capture has finished. */
    onApprove?(data: { orderID: string; payerID?: string }, actions: PayPalActions): Promise<void> | void;
    /** Called when the buyer cancels the popup. */
    onCancel?(data: { orderID: string; payerID?: string }): void;
    /** Called on a fatal SDK error (network, configuration, etc). */
    onError?(err: Error): void;
    /** Called when the buyer clicks the button (analytics). */
    onClick?(): void;
    /** Called when the button is ready to be shown. */
    onInit?(): void;
    /** Called when the button is fully ready. */
    onShippingChange?(): void;
    /** Style the approved PayPal button. */
    style?: PayPalButtonStyle;
  }

  interface PayPalActions {
    redirect(url: string): void;
    close(): void;
  }

  interface PayPalButtonsInstance {
    isEligible(): boolean;
    render(container: HTMLElement | string): Promise<void>;
    close(): void;
  }

  interface PayPalButtonStyle {
    layout?: "horizontal" | "vertical";
    color?: "gold" | "blue" | "silver" | "white" | "black";
    shape?: "rect" | "pill";
    height?: number;
    label?: "paypal" | "checkout" | "buynow" | "pay";
    tagline?: boolean;
  }
}
