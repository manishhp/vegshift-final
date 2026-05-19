import React, { createContext, useContext, useMemo, useState } from "react";

export type FarmerProfile = {
  desiredCrop: string;
};

interface FarmerProfileState {
  profile: FarmerProfile;
  hasSubmitted: boolean;
  setProfile: (profile: FarmerProfile) => void;
  markSubmitted: () => void;
}

const defaultProfile: FarmerProfile = {
  desiredCrop: "",
};

const FarmerProfileContext = createContext<FarmerProfileState | undefined>(undefined);

export const FarmerProfileProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [profile, setProfile] = useState<FarmerProfile>(defaultProfile);
  const [hasSubmitted, setHasSubmitted] = useState(false);

  const markSubmitted = () => setHasSubmitted(true);

  const value = useMemo(
    () => ({ profile, hasSubmitted, setProfile, markSubmitted }),
    [profile, hasSubmitted]
  );

  return <FarmerProfileContext.Provider value={value}>{children}</FarmerProfileContext.Provider>;
};

export function useFarmerProfile() {
  const ctx = useContext(FarmerProfileContext);
  if (!ctx) {
    throw new Error("useFarmerProfile must be used within FarmerProfileProvider");
  }
  return ctx;
}
