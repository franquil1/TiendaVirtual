from django.shortcuts import render, get_object_or_404, redirect
from .models import Producto
from .carrito import Carrito
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login, logout, authenticate
from .forms import RegistroUsuarioForm
from .models import Pedido, DetallePedido
from decimal import Decimal
from django.contrib.auth.decorators import login_required
from urllib.parse import quote
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Sum
from django.contrib.auth.models import User
from django.shortcuts import render, redirect
from .models import Producto
from django.utils.text import slugify
from django.contrib.auth.decorators import user_passes_test


def index(request):
    return render(request, 'TiendaApp/index.html')




def index(request):

    productos = Producto.objects.all()[:8]

    return render(request, 'TiendaApp/index.html', {
        'productos': productos
    })


def productos(request):

    buscar = request.GET.get('buscar')

    productos = Producto.objects.all()

    if buscar:
        productos = productos.filter(
            nombre__icontains=buscar
        )

    return render(request, 'TiendaApp/productos.html', {
        'productos': productos
    })

def detalle_producto(request, slug):

    producto = get_object_or_404(
        Producto,
        slug=slug
    )

    relacionados = Producto.objects.exclude(
        id=producto.id
    )[:4]

    return render(request,
        'TiendaApp/detalle_producto.html',
        {
            'producto': producto,
            'relacionados': relacionados
        }
    )

# carrito de compras

def agregar_producto(request, producto_id):

    carrito = Carrito(request)

    producto = Producto.objects.get(id=producto_id)

    carrito.agregar(producto)

    return redirect('carrito')


def eliminar_producto(request, producto_id):

    carrito = Carrito(request)

    producto = Producto.objects.get(id=producto_id)

    carrito.eliminar(producto)

    return redirect('carrito')


def restar_producto(request, producto_id):

    carrito = Carrito(request)

    producto = Producto.objects.get(id=producto_id)

    carrito.restar(producto)

    return redirect('carrito')


def limpiar_carrito(request):

    carrito = Carrito(request)

    carrito.limpiar()

    return redirect('carrito')


def carrito(request):

    return render(request,
        'TiendaApp/carrito.html'
    )

#formilario de registro 
def registro(request):

    if request.method == 'POST':

        form = RegistroUsuarioForm(request.POST)

        if form.is_valid():

            usuario = form.save()

            login(request, usuario)

            return redirect('index')

    else:

        form = RegistroUsuarioForm()

    return render(request,
        'TiendaApp/registro.html',
        {
            'form': form
        }
    )


def iniciar_sesion(request):

    if request.method == 'POST':

        form = AuthenticationForm(
            request,
            data=request.POST
        )

        if form.is_valid():

            username = form.cleaned_data.get('username')

            password = form.cleaned_data.get('password')

            usuario = authenticate(
                username=username,
                password=password
            )

            if usuario is not None:

                login(request, usuario)

                return redirect('index')

    else:

        form = AuthenticationForm()

    return render(request,
        'TiendaApp/login.html',
        {
            'form': form
        }
    )


def cerrar_sesion(request):

    logout(request)

    return redirect('index')


@login_required
def checkout(request):

    if request.method == 'POST':

        nombre = request.POST.get('nombre')
        email = request.POST.get('email')
        telefono = request.POST.get('telefono')
        direccion = request.POST.get('direccion')
        ciudad = request.POST.get('ciudad')

        carrito = request.session.get('carrito', {})

        total = Decimal('0.00')

        # Construir resumen del pedido para WhatsApp
        mensaje = (
            f"Hola! 👋 Acabo de realizar un pago por Nequi "
            f"y quiero confirmar mi pedido:%0A%0A"
        )

        for key, value in carrito.items():

            subtotal = (
                Decimal(str(value['precio']))
                * value['cantidad']
            )

            total += subtotal

            mensaje += (
                f"🛍 Producto: {value['nombre']}%0A"
                f"   Cantidad: {value['cantidad']}%0A"
                f"   Subtotal: ${subtotal:,.0f}%0A%0A"
            )

        # Crear pedido en la base de datos
        pedido = Pedido.objects.create(
            usuario=request.user,
            nombre=nombre,
            email=email,
            telefono=telefono,
            direccion=direccion,
            ciudad=ciudad,
            total=total
        )

        for key, value in carrito.items():

            subtotal = (
                Decimal(str(value['precio']))
                * value['cantidad']
            )

            producto = Producto.objects.get(
                id=value['producto_id']
            )

            DetallePedido.objects.create(
                pedido=pedido,
                producto=producto,
                cantidad=value['cantidad'],
                precio=value['precio'],
                subtotal=subtotal
            )

        # Completar mensaje WhatsApp
        mensaje += (
            f"💰 TOTAL PAGADO POR NEQUI: ${total:,.0f}%0A%0A"
            f"📋 Pedido #: {pedido.id}%0A"
            f"👤 Nombre: {nombre}%0A"
            f"📞 Teléfono: {telefono}%0A"
            f"🏙 Ciudad: {ciudad}%0A"
            f"📍 Dirección: {direccion}"
        )

        # Limpiar carrito
        request.session['carrito'] = {}

        numero_whatsapp = "573136202509"
        whatsapp_url = f"https://wa.me/{numero_whatsapp}?text={mensaje}"

        return render(request, 'TiendaApp/checkout.html', {
            'mostrar_pago': True,
            'total': f"{total:,.0f}",
            'pedido_id': pedido.id,
            'whatsapp_url': whatsapp_url,
        })

    return render(request, 'TiendaApp/checkout.html', {
        'mostrar_pago': False,
    })


@staff_member_required
def dashboard(request):

    total_productos = Producto.objects.count()

    total_pedidos = Pedido.objects.count()

    total_usuarios = User.objects.count()

    ventas_totales = Pedido.objects.aggregate(
        total=Sum('total')
    )['total'] or 0

    pedidos_recientes = Pedido.objects.order_by(
        '-fecha'
    )[:5]

    productos = Producto.objects.all()

    pedidos = Pedido.objects.all().order_by(
        '-fecha'
    )

    usuarios = User.objects.all()

    contexto = {
        'total_productos': total_productos,
        'total_pedidos': total_pedidos,
        'total_usuarios': total_usuarios,
        'ventas_totales': ventas_totales,
        'pedidos_recientes': pedidos_recientes,
        'productos': productos,
        'pedidos': pedidos,
        'usuarios': usuarios,
    }

    return render(
        request,
        'TiendaApp/dashboard.html',
        contexto
    )

@staff_member_required
def eliminar_producto_admin(request, producto_id):

    producto = get_object_or_404(
        Producto,
        id=producto_id
    )

    producto.delete()

    return redirect('/dashboard/#productos')


@staff_member_required
def eliminar_pedido_admin(request, pedido_id):

    pedido = get_object_or_404(
        Pedido,
        id=pedido_id
    )

    pedido.delete()

    return redirect('/dashboard/#productos')


@staff_member_required
def eliminar_usuario_admin(request, usuario_id):

    usuario = get_object_or_404(
        User,
        id=usuario_id
    )

    if not usuario.is_superuser:
        usuario.delete()

    return redirect('/dashboard/#productos')
@login_required
def mis_pedidos(request):

    pedidos = Pedido.objects.filter(
        usuario=request.user
    ).order_by('-fecha')

    return render(
        request,
        'TiendaApp/mis_pedidos.html',
        {
            'pedidos': pedidos
        }
    )

@login_required
def detalle_pedido(request, pedido_id):

    pedido = get_object_or_404(
        Pedido,
        id=pedido_id,
        usuario=request.user
    )

    detalles = DetallePedido.objects.filter(
        pedido=pedido
    )

    return render(
        request,
        'TiendaApp/detalle_pedido.html',
        {
            'pedido': pedido,
            'detalles': detalles
        }
    )

@user_passes_test(lambda u: u.is_superuser)
def crear_producto(request):

    if request.method == 'POST':

        nombre = request.POST['nombre']
        precio = request.POST['precio']
        descripcion = request.POST['descripcion']
        imagen = request.FILES['imagen']

        Producto.objects.create(
            nombre=nombre,
            precio=precio,
            descripcion=descripcion,
            imagen=imagen,
            slug=slugify(nombre)
        )

        return redirect('/dashboard/#productos')

    return render(request, 'TiendaApp/crear_producto.html')
