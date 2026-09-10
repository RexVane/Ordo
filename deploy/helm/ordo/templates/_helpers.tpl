{{- define "ordo.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "ordo.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- $name := include "ordo.name" . -}}
{{- if contains $name .Release.Name -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}
{{- end -}}

{{- define "ordo.labels" -}}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version | replace "+" "_" }}
app.kubernetes.io/name: {{ include "ordo.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}

{{- define "ordo.selectorLabels" -}}
app.kubernetes.io/name: {{ include "ordo.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{- define "ordo.secretName" -}}
{{- if .Values.existingSecretName -}}
{{- .Values.existingSecretName -}}
{{- else -}}
{{- printf "%s-env" (include "ordo.fullname" .) -}}
{{- end -}}
{{- end -}}

{{- define "ordo.serviceAccountName" -}}
{{- if .Values.serviceAccount.name -}}
{{- .Values.serviceAccount.name -}}
{{- else -}}
{{- include "ordo.fullname" . -}}
{{- end -}}
{{- end -}}

{{/*
Render serviceAccountName when the chart creates or references a ServiceAccount.
*/}}
{{- define "ordo.serviceAccountNameBlock" -}}
{{- if or .Values.serviceAccount.create .Values.serviceAccount.name -}}
serviceAccountName: {{ include "ordo.serviceAccountName" . }}
{{- end -}}
{{- end -}}

{{/*
Render imagePullSecrets block when configured.
*/}}
{{- define "ordo.imagePullSecretsBlock" -}}
{{- with .Values.imagePullSecrets -}}
imagePullSecrets:
{{ toYaml . | nindent 2 }}
{{- end -}}
{{- end -}}

{{/*
Render a merged podSecurityContext block.

Inputs:
- root: the chart root context (.)
- extra: component-specific podSecurityContext overrides (map)
*/}}
{{- define "ordo.podSecurityContext" -}}
{{- $root := .root -}}
{{- $extra := .extra -}}
{{- $ctx := dict -}}
{{- with $root.Values.security.podSecurityContext -}}
{{- $ctx = mergeOverwrite $ctx . -}}
{{- end -}}
{{- if $root.Values.security.hardened -}}
{{- with $root.Values.security.hardenedPodSecurityContext -}}
{{- $ctx = mergeOverwrite $ctx . -}}
{{- end -}}
{{- end -}}
{{- with $extra -}}
{{- $ctx = mergeOverwrite $ctx . -}}
{{- end -}}
{{- if $ctx -}}
podSecurityContext:
{{ toYaml $ctx | nindent 2 }}
{{- end -}}
{{- end -}}

{{/*
Render a merged container securityContext block.

Inputs:
- root: the chart root context (.)
- extra: component-specific securityContext overrides (map)
*/}}
{{- define "ordo.containerSecurityContext" -}}
{{- $root := .root -}}
{{- $extra := .extra -}}
{{- $ctx := dict -}}
{{- with $root.Values.security.containerSecurityContext -}}
{{- $ctx = mergeOverwrite $ctx . -}}
{{- end -}}

{{- if $root.Values.security.hardened -}}
{{- with $root.Values.security.hardenedContainerSecurityContext -}}
{{- $ctx = mergeOverwrite $ctx . -}}
{{- end -}}
{{- end -}}
{{- with $extra -}}
{{- $ctx = mergeOverwrite $ctx . -}}
{{- end -}}
{{- if $ctx -}}
securityContext:
{{ toYaml $ctx | nindent 2 }}
{{- end -}}
{{- end -}}

{{/*
Render automountServiceAccountToken for a pod spec.

Why helper: Helm's `default` treats boolean false as "empty", which makes it
hard to override a global true -> per-component false. We use a nil-aware
override instead.

Inputs:
- root: chart root context (.)
- override: component-level override (bool or nil)
*/}}
{{- define "ordo.automountServiceAccountToken" -}}
{{- $root := .root -}}
{{- $override := .override -}}
{{- $val := $root.Values.automountServiceAccountToken -}}
{{- if kindIs "bool" $override -}}
{{- $val = $override -}}
{{- end -}}
automountServiceAccountToken: {{ $val }}
{{- end -}}

{{/*
Look up a named env var in a pod env list.
Returns an empty string when the var is absent.
*/}}
{{- define "ordo.envLookup" -}}
{{- $name := printf "%v" (.name | default "") -}}
{{- $value := "" -}}
{{- range .env -}}
{{- if eq (printf "%v" (.name | default "")) $name -}}
{{- $value = printf "%v" (.value | default "") -}}
{{- end -}}
{{- end -}}
{{- $value -}}
{{- end -}}
