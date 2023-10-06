{{/*
Return the proper input image name
*/}}
{{- define "input.image" -}}
{{ include "common.images.image" (dict "imageRoot" .Values.input.image "global" .Values.global) }}
{{- end -}}

{{/*
Return the proper image name (for the init container volume-permissions image)
*/}}
{{- define "input.volumePermissions.image" -}}
{{- include "common.images.image" ( dict "imageRoot" .Values.volumePermissions.image "global" .Values.global ) -}}
{{- end -}}

{{/*
Return the proper Docker Image Registry Secret Names
*/}}
{{- define "input.imagePullSecrets" -}}
{{- include "common.images.pullSecrets" (dict "images" (list .Values.input.image .Values.input.image .Values.volumePermissions.image) "global" .Values.global) -}}
{{- end -}}

{{/*
Return the proper output image name
*/}}
{{- define "output.image" -}}
{{ include "common.images.image" (dict "imageRoot" .Values.output.image "global" .Values.global) }}
{{- end -}}

{{/*
Return the proper image name (for the init container volume-permissions image)
*/}}
{{- define "output.volumePermissions.image" -}}
{{- include "common.images.image" ( dict "imageRoot" .Values.volumePermissions.image "global" .Values.global ) -}}
{{- end -}}

{{/*
Return the proper Docker Image Registry Secret Names
*/}}
{{- define "output.imagePullSecrets" -}}
{{- include "common.images.pullSecrets" (dict "images" (list .Values.output.image .Values.output.image .Values.volumePermissions.image) "global" .Values.global) -}}
{{- end -}}

{{/*
Return the proper worker image name
*/}}
{{- define "worker.image" -}}
{{ include "common.images.image" (dict "imageRoot" .Values.worker.image "global" .Values.global) }}
{{- end -}}

{{/*
Return the proper image name (for the init container volume-permissions image)
*/}}
{{- define "worker.volumePermissions.image" -}}
{{- include "common.images.image" ( dict "imageRoot" .Values.volumePermissions.image "global" .Values.global ) -}}
{{- end -}}

{{/*
Return the proper Docker Image Registry Secret Names
*/}}
{{- define "worker.imagePullSecrets" -}}
{{- include "common.images.pullSecrets" (dict "images" (list .Values.worker.image .Values.worker.image .Values.volumePermissions.image) "global" .Values.global) -}}
{{- end -}}

{{/*
Return the proper proxy image name
*/}}
{{- define "proxy.image" -}}
{{ include "common.images.image" (dict "imageRoot" .Values.proxy.image "global" .Values.global) }}
{{- end -}}

{{/*
Return the proper image name (for the init container volume-permissions image)
*/}}
{{- define "proxy.volumePermissions.image" -}}
{{- include "common.images.image" ( dict "imageRoot" .Values.volumePermissions.image "global" .Values.global ) -}}
{{- end -}}

{{/*
Return the proper Docker Image Registry Secret Names
*/}}
{{- define "proxy.imagePullSecrets" -}}
{{- include "common.images.pullSecrets" (dict "images" (list .Values.proxy.image .Values.proxy.image .Values.volumePermissions.image) "global" .Values.global) -}}
{{- end -}}

{{/*
Return the proper input URI
*/}}"
{{- define "input.video.uri" -}}
{{- if .Values.input.video.uri -}}
{{- .Values.input.video.uri -}}
{{- else -}}
rtmp://{{- include "common.names.fullname" . }}-proxy:{{- .Values.proxy.service.ports.video -}}/pipeless/input
{{- end -}}
{{- end -}}

{{/*
Return the proper output URI
*/}}"
{{- define "output.video.uri" -}}
{{- if .Values.output.video.uri -}}
{{- .Values.output.video.uri -}}
{{- else -}}
rtmp://{{- include "common.names.fullname" . }}-proxy:{{- .Values.proxy.service.ports.video -}}/pipeless/output
{{- end -}}
{{- end -}}
