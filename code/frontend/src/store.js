import { configureStore } from "@reduxjs/toolkit";

import trialsReducer from "./features/trials/trialsSlice.js";

export const store = configureStore({
  reducer: {
    trials: trialsReducer,
  },
});
