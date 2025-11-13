import { Bars3Icon } from "@heroicons/react/24/outline";
import { MagnifyingGlassIcon } from "@heroicons/react/24/solid";
import clsx from "clsx";
import EndavaLogo from "../components/EndavaLogo";

interface HeaderProps {
  onToggleSidebar: () => void;
}

const Header = ({ onToggleSidebar }: HeaderProps) => {
  return (
    <header className="sticky top-0 z-30 border-b border-brand-border/60 bg-brand-surface/95 text-white backdrop-blur">
      <div className="mx-auto flex w-full max-w-[1440px] items-center justify-between gap-4 px-6 py-4">
        <EndavaLogo className="h-8 w-auto" wordmarkColor="#FFFFFF" accentColor="#FF5641" />

        <div className="hidden flex-1 items-center justify-center md:flex">
          <div className="relative w-full max-w-lg text-brand-secondary">
            <MagnifyingGlassIcon className="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-brand-secondary/70" />
            <input
              type="search"
              placeholder="Search sessions, labels, actions..."
              className="w-full rounded-full border border-transparent bg-brand-surfaceAlt/80 py-2.5 pl-12 pr-4 text-sm text-white placeholder:text-brand-secondary/60 focus:border-brand-accent/70 focus:outline-none focus:ring-2 focus:ring-brand-accent/30"
            />
          </div>
        </div>

        <button
          type="button"
          className={clsx(
            "flex h-11 w-11 items-center justify-center rounded-full border border-brand-border/70 bg-brand-surfaceAlt/80",
            "text-brand-secondary transition hover:border-brand-accent hover:text-brand-accent"
          )}
          aria-label="Toggle conversation list"
          onClick={onToggleSidebar}
        >
          <Bars3Icon className="h-6 w-6" />
        </button>
      </div>
    </header>
  );
};

export default Header;
