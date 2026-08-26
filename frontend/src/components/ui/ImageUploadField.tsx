
"use client";

/**
 * Campo reutilizable para ingresar imagen.
 * Permite pegar una URL externa O subir un archivo desde el dispositivo.
 * Muestra preview de la imagen seleccionada.
 */

import React, { useState, useRef } from "react";
import { api } from "@/lib/api";

import {
  Box,
  Button,
  TextField,
  Typography,
  CircularProgress,
  Tabs,
  Tab,
  alpha,
} from "@mui/material";
import CloudUploadIcon from "@mui/icons-material/CloudUpload";
import LinkIcon from "@mui/icons-material/Link";
import BrokenImageIcon from "@mui/icons-material/BrokenImage";

interface ImageUploadFieldProps {
  value: string;
  onChange: (url: string) => void;
  label?: string;
}

export default function ImageUploadField({
  value,
  onChange,
  label = "Imagen",
}: ImageUploadFieldProps) {
  const [tab, setTab] = useState<"url" | "upload">("url");
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState("");
  const [imgError, setImgError] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    setUploadError("");
    try {
      const result = await api.upload.image(file);
      // La URL relativa del backend se convierte a URL absoluta
      const absoluteUrl = `${process.env.NEXT_PUBLIC_API_URL?.replace("/api/v1", "") || "http://localhost:8000"}${result.url}`;
      onChange(absoluteUrl);
      setImgError(false);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Error al subir la imagen";
      setUploadError(msg);
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  return (
    <Box>
      <Typography variant="caption" sx={{ fontWeight: 700, color: "text.secondary", mb: 1, display: "block" }}>
        {label}
      </Typography>

      {/* Preview */}
      <Box
        sx={{
          width: "100%",
          height: 180,
          borderRadius: 2,
          overflow: "hidden",
          bgcolor: "action.hover",
          border: "2px dashed",
          borderColor: value && !imgError ? "transparent" : "divider",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          mb: 2,
          position: "relative",
        }}
      >
        {value && !imgError ? (
          <Box
            component="img"
            src={value}
            alt="Preview"
            onError={() => setImgError(true)}
            sx={{ width: "100%", height: "100%", objectFit: "cover" }}
          />
        ) : (
          <Box sx={{ textAlign: "center", color: "text.disabled" }}>
            <BrokenImageIcon sx={{ fontSize: 40, mb: 0.5 }} />
            <Typography variant="caption" sx={{ display: "block" }}>
              {value && imgError ? "URL inválida o sin acceso" : "Sin imagen"}
            </Typography>
          </Box>
        )}
        {uploading && (
          <Box
            sx={{
              position: "absolute",
              inset: 0,
              bgcolor: alpha("#fff", 0.8),
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <CircularProgress size={32} />
          </Box>
        )}
      </Box>

      {/* Tabs: URL vs Upload */}
      <Tabs
        value={tab}
        onChange={(_, v) => setTab(v)}
        variant="fullWidth"
        sx={{ mb: 2, "& .MuiTab-root": { minHeight: 36, fontSize: "0.8rem" } }}
      >
        <Tab value="url" label="Pegar URL" icon={<LinkIcon sx={{ fontSize: 16 }} />} iconPosition="start" />
        <Tab value="upload" label="Subir archivo" icon={<CloudUploadIcon sx={{ fontSize: 16 }} />} iconPosition="start" />
      </Tabs>

      {tab === "url" ? (
        <TextField
          fullWidth
          size="small"
          placeholder="https://ejemplo.com/imagen.jpg"
          value={value}
          onChange={(e) => { onChange(e.target.value); setImgError(false); }}
          slotProps={{ input: { startAdornment: <LinkIcon sx={{ mr: 1, fontSize: 18, color: "text.secondary" }} /> } }}
        />
      ) : (
        <Box>
          <input
            ref={fileRef}
            type="file"
            accept="image/jpeg,image/png,image/webp,image/gif,image/svg+xml"
            style={{ display: "none" }}
            onChange={handleFileChange}
          />
          <Button
            fullWidth
            variant="outlined"
            startIcon={uploading ? <CircularProgress size={16} /> : <CloudUploadIcon />}
            onClick={() => fileRef.current?.click()}
            disabled={uploading}
            sx={{ textTransform: "none" }}
          >
            {uploading ? "Subiendo..." : "Seleccionar imagen (máx. 5 MB)"}
          </Button>
          {uploadError && (
            <Typography variant="caption" color="error" sx={{ mt: 0.5, display: "block" }}>
              {uploadError}
            </Typography>
          )}
          <Typography variant="caption" sx={{ color: "text.disabled", mt: 0.5, display: "block" }}>
            Formatos: JPEG, PNG, WebP, GIF, SVG
          </Typography>
        </Box>
      )}
    </Box>
  );
}
