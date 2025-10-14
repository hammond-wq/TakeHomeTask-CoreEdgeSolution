
import React, { useMemo, useState } from "react";

type Language = "English" | "Spanish" | "Arabic";
type Scenario = "Normal Check-in" | "Delay / ETA Update" | "Breakdown / Emergency";

export type CallTriggerPayload = {
  driverName: string;
  phoneNumber: string; 
  loadNumber: string;
  language: Language;
  scenario: Scenario;
  note?: string;
};

type CallTriggerProps = {
  
  onTrigger?: (payload: CallTriggerPayload) => Promise<void> | void;
 
  disabled?: boolean;
};

const phoneRegex = /^\+?[1-9]\d{7,14}$/; 

const CallTrigger: React.FC<CallTriggerProps> = ({ onTrigger, disabled }) => {
  const [driverName, setDriverName] = useState("");
  const [phoneNumber, setPhoneNumber] = useState("");
  const [loadNumber, setLoadNumber] = useState("");
  const [language, setLanguage] = useState<Language>("English");
  const [scenario, setScenario] = useState<Scenario>("Normal Check-in");
  const [note, setNote] = useState("");

  const [submitting, setSubmitting] = useState(false);
  const [touched, setTouched] = useState<Record<string, boolean>>({});
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const errors = useMemo(() => {
    const e: Record<string, string> = {};
    if (!driverName.trim()) e.driverName = "Driver name is required.";
    if (!phoneRegex.test(phoneNumber.trim()))
      e.phoneNumber = "Enter a valid phone (e.g., +9665XXXXXXXX).";
    if (!loadNumber.trim()) e.loadNumber = "Load / reference number is required.";
    return e;
  }, [driverName, phoneNumber, loadNumber]);

  const hasErrors = Object.keys(errors).length > 0;

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setTouched({ driverName: true, phoneNumber: true, loadNumber: true });
    setSuccessMsg(null);
    setErrorMsg(null);

    if (hasErrors) return;

    const payload: CallTriggerPayload = {
      driverName: driverName.trim(),
      phoneNumber: phoneNumber.trim(),
      loadNumber: loadNumber.trim(),
      language,
      scenario,
      note: note.trim() || undefined,
    };

    try {
      setSubmitting(true);
      if (onTrigger) {
        await onTrigger(payload);
      } else {
        
        console.log("CallTrigger payload:", payload);
        await new Promise((r) => setTimeout(r, 600));
      }
      setSuccessMsg("Test call has been queued successfully.");
    } catch (err: any) {
      setErrorMsg(err?.message || "Failed to queue the test call.");
    } finally {
      setSubmitting(false);
    }
  };

  const baseInput =
    "w-full p-2 rounded border focus:outline-none focus:ring-2 focus:ring-vite-green transition";
  const invalidInput = "border-red-400";
  const validInput = "border-gray-300";

  return (
    <section className="w-full flex justify-center">
      <div className="w-full max-w-2xl bg-white/95 backdrop-blur rounded-2xl shadow-lg hover:shadow-xl transition-shadow duration-300">
        <header className="px-6 pt-6 pb-3 border-b">
          <h2 className="text-2xl font-semibold text-vite-green">Trigger Test Call</h2>
          <p className="text-sm text-gray-500">
            Send an automated, AI-assisted call to a driver and capture a structured update.
          </p>
        </header>

        <form onSubmit={handleSubmit} className="p-6 space-y-5">
       
          <div>
            <label className="block mb-1 font-medium">Driver Name</label>
            <input
              value={driverName}
              onChange={(e) => setDriverName(e.target.value)}
              onBlur={() => setTouched((t) => ({ ...t, driverName: true }))}
              className={`${baseInput} ${
                touched.driverName && errors.driverName ? invalidInput : validInput
              }`}
              placeholder="e.g., Ahmed Al-Qahtani"
              disabled={submitting || disabled}
            />
            {touched.driverName && errors.driverName && (
              <p className="text-sm text-red-600 mt-1">{errors.driverName}</p>
            )}
          </div>

    
          <div>
            <label className="block mb-1 font-medium">Phone Number</label>
            <input
              value={phoneNumber}
              onChange={(e) => setPhoneNumber(e.target.value)}
              onBlur={() => setTouched((t) => ({ ...t, phoneNumber: true }))}
              className={`${baseInput} ${
                touched.phoneNumber && errors.phoneNumber ? invalidInput : validInput
              }`}
              placeholder="+9665XXXXXXXX"
              disabled={submitting || disabled}
              inputMode="tel"
            />
            {touched.phoneNumber && errors.phoneNumber && (
              <p className="text-sm text-red-600 mt-1">{errors.phoneNumber}</p>
            )}
          </div>

     
          <div>
            <label className="block mb-1 font-medium">Load / Reference #</label>
            <input
              value={loadNumber}
              onChange={(e) => setLoadNumber(e.target.value)}
              onBlur={() => setTouched((t) => ({ ...t, loadNumber: true }))}
              className={`${baseInput} ${
                touched.loadNumber && errors.loadNumber ? invalidInput : validInput
              }`}
              placeholder="e.g., LDN-10492"
              disabled={submitting || disabled}
            />
            {touched.loadNumber && errors.loadNumber && (
              <p className="text-sm text-red-600 mt-1">{errors.loadNumber}</p>
            )}
          </div>

      
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block mb-1 font-medium">Language</label>
              <select
                value={language}
                onChange={(e) => setLanguage(e.target.value as Language)}
                className={`${baseInput} ${validInput}`}
                disabled={submitting || disabled}
              >
                <option>English</option>
                <option>Spanish</option>
                <option>Arabic</option>
              </select>
            </div>

            <div>
              <label className="block mb-1 font-medium">Scenario</label>
              <select
                value={scenario}
                onChange={(e) => setScenario(e.target.value as Scenario)}
                className={`${baseInput} ${validInput}`}
                disabled={submitting || disabled}
              >
                <option>Normal Check-in</option>
                <option>Delay / ETA Update</option>
                <option>Breakdown / Emergency</option>
              </select>
            </div>
          </div>

         
          <div>
            <label className="block mb-1 font-medium">Notes (Optional)</label>
            <textarea
              value={note}
              onChange={(e) => setNote(e.target.value)}
              rows={3}
              className={`${baseInput} ${validInput} resize-y`}
              placeholder="Context for the agent (e.g., ask for odometer, confirm temperature logs)…"
              disabled={submitting || disabled}
            />
          </div>

          
          <div className="flex items-center gap-3 pt-2">
            <button
              type="submit"
              disabled={submitting || disabled}
              className="inline-flex items-center justify-center px-5 py-2.5 rounded-lg bg-vite-green text-white font-medium hover:opacity-90 disabled:opacity-60 transition"
            >
              {submitting ? "Queuing…" : "Start Test Call"}
            </button>

            <button
              type="button"
              onClick={() => {
                setDriverName("");
                setPhoneNumber("");
                setLoadNumber("");
                setLanguage("English");
                setScenario("Normal Check-in");
                setNote("");
                setTouched({});
                setSuccessMsg(null);
                setErrorMsg(null);
              }}
              disabled={submitting}
              className="px-4 py-2.5 rounded-lg border border-gray-300 hover:bg-gray-50 transition"
            >
              Reset
            </button>
          </div>

          {/* Messages */}
          {successMsg && (
            <div className="mt-3 text-sm rounded-md bg-green-50 border border-green-200 text-green-700 px-3 py-2">
              {successMsg}
            </div>
          )}
          {errorMsg && (
            <div className="mt-3 text-sm rounded-md bg-red-50 border border-red-200 text-red-700 px-3 py-2">
              {errorMsg}
            </div>
          )}
        </form>
      </div>
    </section>
  );
};

export default CallTrigger;
