import { FormEvent, useState } from "react";

type Props = { onSend: (value: string) => Promise<void>; disabled: boolean };

export function Composer({ onSend, disabled }: Props) {
  const [value, setValue] = useState("");
  const submit = async (event: FormEvent) => {
    event.preventDefault();
    const next = value.trim();
    if (!next || disabled) return;
    setValue("");
    await onSend(next);
  };
  return (
    <form className="composer" onSubmit={submit}>
      <textarea
        value={value}
        onChange={(event) => setValue(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            void submit(event);
          }
        }}
        disabled={disabled}
        placeholder="Ask a product or growth question…"
        aria-label="Ask Lenny Lens"
        rows={2}
      />
      <button className="send-button" disabled={disabled || !value.trim()} type="submit">{disabled ? "Researching…" : "Send"}<span>↗</span></button>
      <p><kbd>Enter</kbd> send · <kbd>Shift Enter</kbd> new line</p>
    </form>
  );
}
