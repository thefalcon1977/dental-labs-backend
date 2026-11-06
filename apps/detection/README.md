# Detection

Upload an image and detect dentin, enamel, and pulp with the local DenseNet checkpoint:

`apps/detection/slm/resolution_best_densenet_model.pth`

That file is listed in `.gitignore` and is not committed.

## Endpoint

`POST /detection/images`

Requires `Authorization: Bearer <access-token>`.

Form field:

- `image` — JPEG, PNG, GIF, or WEBP file

Example:

```bash
curl -X POST http://127.0.0.1:8000/detection/images \
  -H "Authorization: Bearer <access-token>" \
  -F "image=@tooth.jpg"
```

Example response:

```json
{
  "model": "resolution_best_densenet_model.pth",
  "filename": "tooth.jpg",
  "content_type": "image/jpeg",
  "detections": [
    {
      "x1": 0,
      "y1": 0,
      "x2": 224,
      "y2": 224,
      "class_name": "enamel",
      "confidence": 0.97
    }
  ]
}
```

`APP_DETECTION__CONFIDENCE_THRESHOLD` defaults to `0.90`. Restart the API after changing `.env`. Swagger at `http://127.0.0.1:8000/docs` shows the file picker for `image`.
