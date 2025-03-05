<script>
/**
 * 🛠 Shopify Consent Tracking with Cookiebot Integration
 * (made with Cookiebot documentation + enhanced with Chat GPT)
 * This script ensures Shopify respects user consent settings from Cookiebot.
 * It loads Shopify’s Consent Tracking API and applies consent as soon as possible.
 * 
 * ✅ Why is this useful?
 * - Prevents Shopify from setting tracking cookies (_shopify_y, etc.) before consent.
 * - Ensures user choices for analytics, marketing, and preferences are respected.
 * - Reduces unnecessary cookie resets, improving analytics accuracy.
 */

window.Shopify.loadFeatures(
  [{ name: "consent-tracking-api", version: "0.1" }], // Load Shopify's consent tracking API
  function (error) {
    if (error) throw error;

    // ✅ Apply consent immediately if Cookiebot is available
    if ("Cookiebot" in window) {
      const C = Cookiebot.consent;
      window.Shopify.customerPrivacy.setTrackingConsent(
        {
          analytics: C["statistics"],  // Enable if user consents to analytics
          marketing: C["marketing"],   // Enable if user consents to marketing
          preferences: C["preferences"], // Enable if user consents to preferences
          sale_of_data: C["marketing"],  // Matches marketing consent (optional)
        },
        () => console.log("Consent applied before tracking")
      );
    }
  }
);

// ✅ Update consent when Cookiebot finishes loading
window.addEventListener("CookiebotOnConsentReady", function () {
  if (window.Shopify.customerPrivacy) {
    const C = Cookiebot.consent;
    window.Shopify.customerPrivacy.setTrackingConsent(
      {
        analytics: C["statistics"],
        marketing: C["marketing"],
        preferences: C["preferences"],
        sale_of_data: C["marketing"],
      },
      () => console.log("Updated consent applied")
    );
  }
});
</script>
