import { Wordmark } from "@/components/ui";
import { BriefFormMount, SystemStatus } from "@/features/onboarding/OnboardingClient";

const STEPS = [
  ["Describe the business", "A name, what you sell and who for. A rough idea is enough."],
  ["Review the draft", "The assistant proposes a catalogue and a look, and explains each choice. Nothing is saved until you accept."],
  ["Edit and check", "Change anything, then run launch checks that report what passed, what failed and what hasn't been tested yet."],
] as const;

export default function Onboarding() {
  return (
    <div className="mx-auto w-full max-w-[90rem] flex-1 px-5 pb-20 sm:px-8 lg:px-12">
      <header className="flex items-center justify-between py-6">
        <Wordmark />
      </header>

      <div className="grid grid-cols-1 gap-12 pt-6 lg:grid-cols-[minmax(0,26rem)_minmax(0,1fr)] lg:gap-20 lg:pt-14">
        <aside className="flex flex-col gap-10">
          <div>
            <h1 className="font-display text-[2.75rem] leading-[1.04] sm:text-[3.5rem] sm:leading-[1.02]">
              Describe the shop you want to open.
            </h1>
            <p className="mt-5 max-w-[38ch] text-base text-ink-2">
              Launchcraft drafts a storefront and catalogue from your brief, lets you change every detail,
              and only calls the store ready once its checks have actually passed.
            </p>
          </div>

          <ol className="flex flex-col gap-5">
            {STEPS.map(([title, body], i) => (
              <li key={title} className="grid grid-cols-[1.75rem_1fr] gap-x-3">
                <span className="font-display text-xl leading-6 text-stamp tabular">{i + 1}</span>
                <div>
                  <p className="text-sm font-semibold">{title}</p>
                  <p className="mt-0.5 text-sm text-ink-2">{body}</p>
                </div>
              </li>
            ))}
          </ol>

          <SystemStatus />
        </aside>

        <section className="rounded-md border border-rule bg-sheet px-5 py-7 shadow-[var(--shadow-sheet)] sm:px-8 sm:py-9">
          <BriefFormMount />
        </section>
      </div>
    </div>
  );
}
