import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";

import apiClient from "../../api/client.js";

function apiError(error) {
  const detail = error.response?.data?.detail;

  if (Array.isArray(detail)) {
    return detail.map((item) => item.msg).join("; ");
  }

  return detail || error.message || "Request failed";
}

export const fetchTrials = createAsyncThunk(
  "trials/fetchTrials",
  async (_, { rejectWithValue }) => {
    try {
      const response = await apiClient.get("/api/trials", {
        params: { skip: 0, limit: 50 },
      });
      return response.data;
    } catch (error) {
      return rejectWithValue(apiError(error));
    }
  },
);

export const createTrial = createAsyncThunk(
  "trials/createTrial",
  async (trialData, { rejectWithValue }) => {
    try {
      const response = await apiClient.post("/api/trials", trialData);
      return response.data;
    } catch (error) {
      return rejectWithValue(apiError(error));
    }
  },
);

export const updateTrial = createAsyncThunk(
  "trials/updateTrial",
  async ({ id, trialData }, { rejectWithValue }) => {
    try {
      const response = await apiClient.put(`/api/trials/${id}`, trialData);
      return response.data;
    } catch (error) {
      return rejectWithValue(apiError(error));
    }
  },
);

export const deleteTrial = createAsyncThunk(
  "trials/deleteTrial",
  async (id, { rejectWithValue }) => {
    try {
      await apiClient.delete(`/api/trials/${id}`);
      return id;
    } catch (error) {
      return rejectWithValue(apiError(error));
    }
  },
);

const trialsSlice = createSlice({
  name: "trials",
  initialState: {
    items: [],
    loading: false,
    error: null,
  },
  reducers: {
    clearError(state) {
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchTrials.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchTrials.fulfilled, (state, action) => {
        state.loading = false;
        state.items = action.payload;
      })
      .addCase(fetchTrials.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      })
      .addCase(createTrial.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(createTrial.fulfilled, (state, action) => {
        state.loading = false;
        state.items.unshift(action.payload);
      })
      .addCase(createTrial.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      })
      .addCase(updateTrial.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(updateTrial.fulfilled, (state, action) => {
        state.loading = false;
        const index = state.items.findIndex(
          (trial) => trial.id === action.payload.id,
        );
        if (index >= 0) {
          state.items[index] = action.payload;
        } else {
          state.items.unshift(action.payload);
        }
      })
      .addCase(updateTrial.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      })
      .addCase(deleteTrial.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(deleteTrial.fulfilled, (state, action) => {
        state.loading = false;
        state.items = state.items.filter(
          (trial) => trial.id !== action.payload,
        );
      })
      .addCase(deleteTrial.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      });
  },
});

export const { clearError } = trialsSlice.actions;
export default trialsSlice.reducer;
