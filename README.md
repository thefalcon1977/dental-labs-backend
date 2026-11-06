# Microservices FastAPI Template

A production-ready template for building microservices applications with modern architecture and best practices.

## What It Does

This template provides a foundation for building scalable microservices applications. It includes essential infrastructure, patterns, and tools needed to develop, deploy, and maintain production-ready services.

## Who It's For

- **Development Teams** - Teams building new microservices or modernizing existing applications
- **Product Teams** - Teams needing a reliable, scalable foundation for new services
- **Organizations** - Organizations standardizing their microservices architecture

## Key Features

- **Scalable Architecture** - Built for high performance and scalability
- **Production Ready** - Includes monitoring, logging, and health checks out of the box
- **Modern Standards** - Follows current best practices and industry standards
- **Easy to Extend** - Modular design makes it easy to add new features and services
- **Well Documented** - Comprehensive documentation and development guidelines

## Getting Started

To get started with this template, contact your development team or see the technical documentation for setup instructions.

## Detection API

`apps/detection` accepts an image and runs the local DenseNet checkpoint `apps/detection/slm/resolution_best_densenet_model.pth`. It returns dentin, enamel, and pulp regions. The checkpoint is gitignored.

```bash
curl -X POST http://127.0.0.1:8000/detection/images \
  -H "Authorization: Bearer <access-token>" \
  -F "image=@tooth.jpg"
```

See `apps/detection/README.md`.

## Documentation

For technical details, setup instructions, development guidelines, and API documentation, see:

- **`.cursor/rules/`** - Development standards, architecture patterns, and technical guidelines
- **`docs/`** - Additional documentation (if available)

Technical documentation includes:
- Architecture and project structure
- Development setup and configuration
- API endpoints and usage
- Database setup and migrations
- Testing and deployment guides

---

**Note**: This is a template project. Customize it according to your business needs!
