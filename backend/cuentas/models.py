from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.db import models
from django.db.models.functions import Now

ROL_ADMINISTRADOR = "administrador"
ROL_VENDEDOR = "vendedor"
ROL_DESPACHADOR = "despachador"
ROL_CLIENTE = "cliente"
ROLES = (ROL_ADMINISTRADOR, ROL_VENDEDOR, ROL_DESPACHADOR, ROL_CLIENTE)


class Rol(models.Model):
    id_rol = models.SmallAutoField(primary_key=True)
    nombre = models.CharField(max_length=30, unique=True)

    class Meta:
        db_table = "roles"
        verbose_name = "rol"
        verbose_name_plural = "roles"

    def __str__(self):
        return self.nombre


class UsuarioManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, rol=None, **extra):
        if not email:
            raise ValueError("El email es obligatorio")
        if rol is None:
            rol, _ = Rol.objects.get_or_create(nombre=ROL_CLIENTE)
        elif isinstance(rol, str):
            rol, _ = Rol.objects.get_or_create(nombre=rol)
        usuario = self.model(email=self.normalize_email(email).lower(), rol=rol, **extra)
        usuario.set_password(password)
        usuario.save(using=self._db)
        return usuario

    def create_superuser(self, email, password=None, **extra):
        return self.create_user(email, password, rol=ROL_ADMINISTRADOR, **extra)


class Usuario(AbstractBaseUser):
    """Tabla `usuarios`. Sin columnas extra: no usa PermissionsMixin ni last_login."""

    id_usuario = models.BigAutoField(primary_key=True)
    email = models.EmailField(max_length=120, unique=True)
    password = models.CharField("contraseña", max_length=255, db_column="password_hash")
    rol = models.ForeignKey(Rol, on_delete=models.PROTECT, db_column="id_rol", related_name="usuarios")
    activo = models.BooleanField(default=True, db_default=True)
    fecha_creacion = models.DateTimeField(db_default=Now())

    last_login = None  # la tabla `usuarios` no tiene esta columna

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UsuarioManager()

    class Meta:
        db_table = "usuarios"
        verbose_name = "usuario"
        verbose_name_plural = "usuarios"

    def __str__(self):
        return self.email

    @property
    def nombre_rol(self) -> str:
        return self.rol.nombre

    # --- Integracion con django.contrib.auth / admin ---
    @property
    def is_active(self):
        return self.activo

    @property
    def is_staff(self):
        return self.activo and self.rol.nombre == ROL_ADMINISTRADOR

    @property
    def is_superuser(self):
        return self.is_staff

    def has_perm(self, perm, obj=None):
        return self.is_staff

    def has_perms(self, perm_list, obj=None):
        return self.is_staff

    def has_module_perms(self, app_label):
        return self.is_staff
