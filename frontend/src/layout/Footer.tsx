const Footer = () => {
  return (
    <footer className="border-t border-brand-border/60 bg-brand-surface/90 py-6 text-sm text-brand-secondary/70">
      <div className="relative mx-auto flex w-full max-w-[1440px] flex-col items-center gap-4 px-6 text-sm md:flex-row md:items-center md:justify-start">
        <p className="order-1 w-full text-center text-sm text-white/80 md:order-2 md:w-auto md:absolute md:left-1/2 md:top-1/2 md:-translate-x-1/2 md:-translate-y-1/2">
          © {new Date().getFullYear()} Endava. All rights reserved.
        </p>

        <nav className="order-2 flex flex-wrap items-center justify-center gap-4 md:order-1 md:mr-auto md:justify-start">
          <a
            href="https://www.endava.com/"
            target="_blank"
            rel="noreferrer"
            className="transition hover:text-white"
          >
            Company
          </a>
          <a
            href="https://www.endava.com/contact"
            target="_blank"
            rel="noreferrer"
            className="transition hover:text-white"
          >
            Contact
          </a>
          <a
            href="https://www.endava.com/legal/privacy-notice"
            target="_blank"
            rel="noreferrer"
            className="transition hover:text-white"
          >
            Privacy
          </a>
          <a
            href="https://www.endava.com/insights"
            target="_blank"
            rel="noreferrer"
            className="transition hover:text-white"
          >
            Insights
          </a>
        </nav>

      </div>
    </footer>
  );
};

export default Footer;
